from django.conf import settings


def test_settings_load():
    assert settings.MODEL_TEXT == "gemini-3.5-flash"
    assert settings.RENDER_CAP == 8
