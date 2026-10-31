"""Project lookup, create and update, plus small helpers (id parsing, primary photo, file bytes) shared by other managers.

Miesign · Author: Mihir Kapildev Tiwari
"""

import uuid

from core.catalog import load_cities
from core.errors import AppError
from core.models import Photo, Project

MAX_NAME = 80


def parse_id(value, field="id"):
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise AppError("INVALID_ID", f"{field} is not a valid id.")


def create(name=None):
    return Project.objects.create(name=(name or "My house")[:MAX_NAME])


def get_project(project_id):
    project = Project.objects.filter(id=parse_id(project_id, "project_id")).first()
    if project is None:
        raise AppError("NOT_FOUND", "Project not found. Check the link.", status=404)
    return project


def update(project, name=None, state=None, city=None):
    if name is not None:
        project.name = str(name)[:MAX_NAME] or project.name
    if state is not None:
        if state and state not in {s["name"] for s in load_cities()}:
            raise AppError("INVALID_STATE", f"'{state}' is not a state we know.")
        project.state = state
    if city is not None:
        project.city = str(city).strip()[:MAX_NAME]
    project.save()
    return project


def primary_photo(project):
    photo = Photo.objects.filter(id=project.primary_photo_id).first() if project.primary_photo_id else None
    if photo is None:
        raise AppError("NO_PHOTO", "Upload a usable photo of your house first.")
    return photo


def read_bytes(photo):
    with photo.file.open("rb") as f:
        return f.read()
