from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.catalog import load_catalog, load_cities
from core.errors import AppError
from core.managers import designs, estimates, photos, projects, rates, report, structure
from core.serializers import design_dict, project_dict


def _project(request, key="project_id"):
    return projects.get_project(request.query_params.get(key))


@api_view(["POST"])
def project_create(request):
    return Response(project_dict(request, projects.create(request.data.get("name"))))


@api_view(["GET"])
def project_get(request):
    return Response(project_dict(request, _project(request, "id")))


@api_view(["POST"])
def project_update(request):
    project = projects.update(_project(request, "id"), name=request.data.get("name"),
                              state=request.data.get("state"), city=request.data.get("city"))
    return Response(project_dict(request, project))


@api_view(["POST"])
def photo_upload(request):
    project = _project(request)
    uploaded = request.FILES.get("file")
    if uploaded is None:
        raise AppError("NO_FILE", "Choose a photo to upload.")
    photos.upload(project, uploaded)
    project.refresh_from_db()
    return Response(project_dict(request, project))


@api_view(["POST"])
def photo_set_primary(request):
    project = photos.set_primary(_project(request), projects.parse_id(request.data.get("photo_id"), "photo_id"))
    return Response(project_dict(request, project))


@api_view(["POST"])
def structure_detect(request):
    project = _project(request)
    structure.detect(project)
    project.refresh_from_db()
    return Response(project_dict(request, project))


@api_view(["POST"])
def structure_save(request):
    project = _project(request)
    structure.save(project, request.data.get("components"))
    project.refresh_from_db()
    return Response(project_dict(request, project))


@api_view(["POST"])
def scale_set(request):
    project = structure.set_scale(
        _project(request), component_id=request.data.get("component_id"),
        real_height_ft=request.data.get("real_height_ft"), use_default=bool(request.data.get("use_default")),
    )
    return Response(project_dict(request, project))


@api_view(["GET"])
def catalog(request):
    return Response({"materials": list(load_catalog().values())})


@api_view(["GET"])
def locations(request):
    return Response({"states": load_cities()})


@api_view(["GET"])
def rates_get(request):
    pid = request.query_params.get("project_id")
    project_id = projects.parse_id(pid, "project_id") if pid else None
    rows = rates.get_rates(request.query_params.get("state", ""), request.query_params.get("city", ""), project_id)
    return Response({"rates": list(rows.values())})


@api_view(["POST"])
def rates_override(request):
    project = _project(request)
    rates.set_override(project.id, request.data.get("material_id"),
                       request.data.get("material_rate"), request.data.get("labor_rate"))
    rows = rates.get_rates(project.state, project.city, project_id=project.id)
    return Response({"rates": list(rows.values())})


@api_view(["POST"])
def design_from_text(request):
    design = designs.from_text(_project(request), request.data.get("text"))
    return Response({"designs": [design_dict(request, design)]})


@api_view(["POST"])
def design_recommend(request):
    created = designs.recommend(_project(request), request.data)
    return Response({"designs": [design_dict(request, d) for d in created]})


@api_view(["POST"])
def design_save(request):
    design = designs.save(_project(request), request.data.get("id"), request.data.get("name"),
                          request.data.get("spec"))
    return Response({"designs": [design_dict(request, design)]})


@api_view(["POST"])
def design_render(request):
    design = designs.render(designs.get_design(request.query_params.get("id")))
    return Response(design_dict(request, design))


@api_view(["GET"])
def estimate_get(request):
    return Response(estimates.for_design(designs.get_design(request.query_params.get("design_id"))))


@api_view(["GET"])
def report_get(request):
    design = designs.get_design(request.query_params.get("design_id"))
    response = HttpResponse(report.for_design(design), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="renovation-estimate-{design.id}.pdf"'
    return response
