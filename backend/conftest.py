"""Pytest fixtures shared by all tests; keeps uploaded files out of the real media folder.

Miesign · Author: Mihir Kapildev Tiwari
"""

import pytest


@pytest.fixture(autouse=True)
def tmp_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
