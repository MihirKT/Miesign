from types import SimpleNamespace

import pytest

from core import ai


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def fake_client(monkeypatch, *responses):
    models = FakeModels(responses)
    monkeypatch.setattr(ai, "client", lambda: SimpleNamespace(models=models))
    monkeypatch.setattr(ai, "RETRY_DELAY_SECONDS", 0)
    return models


def text_response(text):
    return SimpleNamespace(text=text, candidates=[SimpleNamespace(grounding_metadata=None)])


def test_detect_structure_filters_unknown_types(monkeypatch):
    fake_client(monkeypatch, text_response(
        '{"components": [{"type": "wall", "box_2d": [0, 0, 500, 1000], "floor": 0, "confidence": 0.9},'
        ' {"type": "car", "box_2d": [0, 0, 10, 10]}]}'
    ))
    found = ai.detect_structure(b"img", "image/jpeg", 1000, 800)
    assert found == [{"type": "wall", "quad": [[0.0, 0.0], [1000.0, 0.0], [1000.0, 400.0], [0.0, 400.0]],
                      "floor": 0, "confidence": 0.9}]


def test_retry_once_then_unavailable(monkeypatch):
    models = fake_client(monkeypatch, RuntimeError("boom"), RuntimeError("boom"))
    with pytest.raises(ai.AiUnavailable):
        ai.check_photo(b"img", "image/jpeg")
    assert models.calls == 2


def test_search_rates_attaches_grounding_sources(monkeypatch):
    chunk = SimpleNamespace(web=SimpleNamespace(uri="https://example.in/rates"))
    response = SimpleNamespace(
        text='{"rates": [{"material_id": "x", "material_rate": 20, "labor_rate": 10}]}',
        candidates=[SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=[chunk]))],
    )
    fake_client(monkeypatch, response)
    rows = ai.search_rates("Maharashtra", "Pune", [{"id": "x", "name": "X", "rate_unit": "sqft"}])
    assert rows == [{"material_id": "x", "material_rate": 20, "labor_rate": 10, "sources": ["https://example.in/rates"]}]


def test_render_returns_image_bytes(monkeypatch):
    part = SimpleNamespace(inline_data=SimpleNamespace(data=b"\x89PNG"))
    fake_client(monkeypatch, SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))]))
    assert ai.render(b"img", "image/jpeg", "prompt") == b"\x89PNG"
