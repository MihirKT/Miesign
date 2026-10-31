import uuid

from django.db import models
from django.utils import timezone


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Base(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])


class Project(Base):
    name = models.TextField(default="My house")
    state = models.TextField(blank=True, default="")
    city = models.TextField(blank=True, default="")
    px_per_ft = models.FloatField(null=True, blank=True)
    scale_source = models.TextField(default="default")
    primary_photo_id = models.UUIDField(null=True, blank=True)
    render_count = models.IntegerField(default=0)


class Photo(Base):
    project_id = models.UUIDField(db_index=True)
    file = models.FileField(upload_to="photos/")
    mime = models.TextField(default="image/jpeg")
    width = models.IntegerField()
    height = models.IntegerField()
    quality_ok = models.BooleanField(default=False)
    quality_report = models.JSONField(default=dict)


class Component(Base):
    project_id = models.UUIDField(db_index=True)
    photo_id = models.UUIDField(db_index=True)
    type = models.TextField()
    quad = models.JSONField()
    floor = models.IntegerField(default=0)
    source = models.TextField(default="ai")
    confidence = models.FloatField(null=True, blank=True)


class Design(Base):
    project_id = models.UUIDField(db_index=True)
    name = models.TextField()
    mode = models.TextField()
    input = models.JSONField(default=dict)
    spec = models.JSONField(default=dict)
    rationale = models.TextField(blank=True, default="")
    warnings = models.JSONField(default=list)
    render_file = models.FileField(upload_to="renders/", null=True, blank=True)
    render_spec_hash = models.TextField(blank=True, default="")


class RateCache(Base):
    state = models.TextField()
    city = models.TextField()
    material_id = models.TextField()
    material_rate = models.FloatField()
    labor_rate = models.FloatField()
    source = models.TextField()
    sources = models.JSONField(default=list)
    fetched_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["state", "city", "material_id"], name="uniq_rate_city_material")]


class RateOverride(Base):
    project_id = models.UUIDField(db_index=True)
    material_id = models.TextField()
    material_rate = models.FloatField(null=True, blank=True)
    labor_rate = models.FloatField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project_id", "material_id"], name="uniq_override_project_material")]
