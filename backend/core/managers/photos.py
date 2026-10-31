from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from core import ai
from core.errors import AppError
from core.models import Photo

MAX_SIDE = 2048
THUMB_SIDE = 512
JPEG_QUALITY = 90
LOCAL_TIPS = [
    "Stand across the road so the whole front of the house fits in the frame.",
    "Shoot in daylight and hold the phone steady.",
]


def local_quality(img):
    issues = []
    w, h = img.size
    if min(w, h) < settings.MIN_PHOTO_SIDE:
        issues.append(f"Photo is too small ({w}×{h}). Use at least {settings.MIN_PHOTO_SIDE} px on the short side.")
    gray = img.convert("L")
    gray.thumbnail((THUMB_SIDE, THUMB_SIDE))
    # FIND_EDGES copies the 1px border unfiltered, which adds fake variance on flat images
    if min(gray.size) >= 3:
        edges = gray.filter(ImageFilter.FIND_EDGES).crop((1, 1, gray.width - 1, gray.height - 1))
        if ImageStat.Stat(edges).var[0] < settings.BLUR_MIN_VARIANCE:
            issues.append("Photo looks blurry or flat.")
    return issues


def _normalise(data):
    try:
        img = Image.open(BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise AppError("INVALID_IMAGE", "That file is not a photo we can read. Upload a JPG, PNG or WEBP.")
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return img, buf.getvalue()


def upload(project, uploaded):
    if Photo.objects.filter(project_id=project.id).count() >= settings.MAX_PHOTOS:
        raise AppError("PHOTO_LIMIT", f"A project can hold {settings.MAX_PHOTOS} photos. Delete one first.")
    if uploaded.size > settings.MAX_UPLOAD_BYTES:
        raise AppError("FILE_TOO_LARGE",
                       f"Photo is larger than {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB. Use a smaller photo.")
    img, jpeg = _normalise(uploaded.read())
    issues = local_quality(img)
    tips = list(LOCAL_TIPS) if issues else []
    ok = not issues
    if ok:
        verdict = ai.check_photo(jpeg, "image/jpeg")
        ok = verdict["is_house_exterior"] and verdict["facade_visible"] and not verdict["issues"]
        issues, tips = verdict["issues"], verdict["tips"]
        if not ok and not issues:
            issues = ["We could not see the front of a house clearly."]
    photo = Photo(project_id=project.id, mime="image/jpeg", width=img.width, height=img.height,
                  quality_ok=ok, quality_report={"issues": issues, "tips": tips})
    photo.file.save(f"{photo.id}.jpg", ContentFile(jpeg), save=False)
    photo.save()
    if ok and project.primary_photo_id is None:
        set_primary(project, photo.id)
    return photo


def set_primary(project, photo_id):
    photo = Photo.objects.filter(id=photo_id, project_id=project.id).first()
    if photo is None:
        raise AppError("NOT_FOUND", "Photo not found in this project.", status=404)
    if not photo.quality_ok:
        raise AppError("PHOTO_NOT_USABLE", "That photo did not pass the quality check. Pick another one.")
    project.primary_photo_id = photo.id
    project.px_per_ft = None
    project.scale_source = "default"
    project.save()
    return project
