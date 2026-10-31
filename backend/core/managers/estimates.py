"""Glues one design to its project's parts, scale and rates and runs the pure estimator.

Miesign · Author: Mihir Kapildev Tiwari
"""

from core.catalog import load_catalog
from core.estimation import default_scale, estimate, walls_overlap_warnings
from core.managers import rates
from core.managers.projects import primary_photo
from core.managers.structure import component_dicts
from core.models import Project


def for_design(design):
    project = Project.objects.get(id=design.project_id)
    photo = primary_photo(project)
    components = component_dicts(project)
    # px_per_ft is null until a photo is analysed; fall back to the default rather than failing the estimate.
    px_per_ft = project.px_per_ft or default_scale(components, photo.height)
    rate_rows = rates.get_rates(project.state, project.city, project_id=project.id)
    result = estimate(components, design.spec, load_catalog(), rate_rows, px_per_ft, project.scale_source)
    result["warnings"] = walls_overlap_warnings(components) + result["warnings"]
    result["location"] = {"state": project.state, "city": project.city}
    return result
