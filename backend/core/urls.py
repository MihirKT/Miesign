"""Maps the 18 API endpoints to their view functions.

Miesign · Author: Mihir Kapildev Tiwari
"""

from django.urls import path

from core import views

urlpatterns = [
    path("project/create", views.project_create),
    path("project", views.project_get),
    path("project/update", views.project_update),
    path("photo/upload", views.photo_upload),
    path("photo/set-primary", views.photo_set_primary),
    path("structure/detect", views.structure_detect),
    path("structure/save", views.structure_save),
    path("scale/set", views.scale_set),
    path("catalog", views.catalog),
    path("locations", views.locations),
    path("rates", views.rates_get),
    path("rates/override", views.rates_override),
    path("design/from-text", views.design_from_text),
    path("design/recommend", views.design_recommend),
    path("design/save", views.design_save),
    path("design/render", views.design_render),
    path("estimate", views.estimate_get),
    path("report", views.report_get),
]
