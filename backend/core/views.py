from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.catalog import load_catalog, load_cities
from core.errors import AppError
from core.managers import designs, estimates, photos, projects, rates, report, structure
from core.serializers import design_dict, project_dict


def _body(request):
    if not isinstance(request.data, dict):
        raise AppError("INVALID_BODY", "Send a JSON object in the request body.")
    return request.data


def _is_true(value):
    return value is True or (isinstance(value, str) and value.lower() in ("true", "1"))


def _project(request, key="project_id"):
    return projects.get_project(request.query_params.get(key))


@api_view(["POST"])
def project_create(request):
    return Response(project_dict(request, projects.create(_body(request).get("name"))))


@api_view(["GET"])
def project_get(request):
    return Response(project_dict(request, _project(request, "id")))


@api_view(["POST"])
def project_update(request):
    project = projects.update(_project(request, "id"), name=_body(request).get("name"),
                              state=_body(request).get("state"), city=_body(request).get("city"))
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
    project = photos.set_primary(_project(request), projects.parse_id(_body(request).get("photo_id"), "photo_id"))
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
    structure.save(project, _body(request).get("components"))
    project.refresh_from_db()
    return Response(project_dict(request, project))


@api_view(["POST"])
def scale_set(request):
    project = structure.set_scale(
        _project(request), component_id=_body(request).get("component_id"),
        real_height_ft=_body(request).get("real_height_ft"), use_default=_is_true(_body(request).get("use_default")),
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
    rates.set_override(project.id, _body(request).get("material_id"),
                       _body(request).get("material_rate"), _body(request).get("labor_rate"))
    rows = rates.get_rates(project.state, project.city, project_id=project.id)
    return Response({"rates": list(rows.values())})


@api_view(["POST"])
def design_from_text(request):
    design = designs.from_text(_project(request), _body(request).get("text"))
    return Response({"designs": [design_dict(request, design)]})


@api_view(["POST"])
def design_recommend(request):
    created = designs.recommend(_project(request), _body(request))
    return Response({"designs": [design_dict(request, d) for d in created]})


@api_view(["POST"])
def design_save(request):
    design = designs.save(_project(request), _body(request).get("id"), _body(request).get("name"),
                          _body(request).get("spec"))
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
