import pytest

from core.models import Project


@pytest.mark.django_db
def test_soft_delete_hides_from_default_manager():
    project = Project.objects.create(name="Test")
    project.soft_delete()

    assert Project.objects.filter(id=project.id).count() == 0
    assert Project.all_objects.get(id=project.id).deleted_at is not None


@pytest.mark.django_db
def test_project_defaults():
    project = Project.objects.create()
    assert project.scale_source == "default"
    assert project.render_count == 0
    assert project.px_per_ft is None
