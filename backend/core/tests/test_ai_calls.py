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


def test_non_dict_json_is_unavailable(monkeypatch):
    fake_client(monkeypatch, text_response("[1, 2]"))
    with pytest.raises(ai.AiUnavailable):
        ai.check_photo(b"img", "image/jpeg")


def test_none_text_is_unavailable(monkeypatch):
    fake_client(monkeypatch, text_response(None))
    with pytest.raises(ai.AiUnavailable):
        ai.check_photo(b"img", "image/jpeg")


def test_check_photo_null_and_wrong_typed_lists(monkeypatch):
    fake_client(monkeypatch, text_response('{"issues": null, "tips": "retake"}'))
    out = ai.check_photo(b"img", "image/jpeg")
    assert out["issues"] == [] and out["tips"] == []


def test_detect_structure_skips_bad_items(monkeypatch):
    fake_client(monkeypatch, text_response(
        '{"components": ["junk", {"type": "wall", "box_2d": [0, 0, "x", 10]},'
        ' {"type": "door", "box_2d": [0, 0, 500, 1000], "floor": "G", "confidence": "high"}]}'
    ))
    found = ai.detect_structure(b"img", "image/jpeg", 1000, 800)
    assert len(found) == 1
    assert found[0]["type"] == "door" and found[0]["floor"] == 0 and found[0]["confidence"] is None


def test_render_content_none_is_unavailable(monkeypatch):
    fake_client(monkeypatch, SimpleNamespace(candidates=[SimpleNamespace(content=None)]))
    with pytest.raises(ai.AiUnavailable):
        ai.render(b"img", "image/jpeg", "prompt")


def _rates_response(sources, uris):
    chunks = [SimpleNamespace(web=SimpleNamespace(uri=u)) for u in uris]
    return SimpleNamespace(
        text='{"rates": [{"material_id": "x", "material_rate": 1, "labor_rate": 2, "sources": %s}]}' % sources,
        candidates=[SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=chunks))],
    )


ITEMS = [{"id": "x", "name": "X", "rate_unit": "sqft"}]


def test_search_rates_prefers_grounding_uris(monkeypatch):
    fake_client(monkeypatch, _rates_response('["https://model.example"]', ["https://real.example"]))
    assert ai.search_rates("S", "C", ITEMS)[0]["sources"] == ["https://real.example"]


def test_search_rates_filters_model_sources_to_http(monkeypatch):
    fake_client(monkeypatch, _rates_response('["https://ok.example", "junk", 5]', []))
    assert ai.search_rates("S", "C", ITEMS)[0]["sources"] == ["https://ok.example"]
