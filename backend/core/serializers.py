from django.conf import settings

from core.managers.structure import component_dicts
from core.models import Design, Photo


def _url(request, f):
    return request.build_absolute_uri(f.url) if f else None


def photo_dict(request, p):
    return {"id": str(p.id), "url": _url(request, p.file), "width": p.width, "height": p.height,
            "quality_ok": p.quality_ok, "issues": p.quality_report.get("issues", []),
            "tips": p.quality_report.get("tips", [])}


def design_dict(request, d):
    return {"id": str(d.id), "name": d.name, "mode": d.mode, "input": d.input, "spec": d.spec,
            "rationale": d.rationale, "warnings": d.warnings, "render_url": _url(request, d.render_file),
            "created_at": d.created_at.isoformat()}


def project_dict(request, project):
    photos = Photo.objects.filter(project_id=project.id).order_by("created_at")
    designs = Design.objects.filter(project_id=project.id).order_by("-created_at")
    return {
        "id": str(project.id), "name": project.name, "state": project.state, "city": project.city,
        "px_per_ft": project.px_per_ft, "scale_source": project.scale_source,
        "primary_photo_id": str(project.primary_photo_id) if project.primary_photo_id else None,
        "render_count": project.render_count, "render_cap": settings.RENDER_CAP,
        "photos": [photo_dict(request, p) for p in photos],
        "components": component_dicts(project) if project.primary_photo_id else [],
        "designs": [design_dict(request, d) for d in designs],
    }
