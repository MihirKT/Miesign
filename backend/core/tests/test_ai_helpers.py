import json

import pytest

from core.ai import box_to_quad, build_render_prompt, extract_json

CATALOG = {"slate": {"id": "slate", "name": "Slate", "render_hint": "dark grey slate cladding"}}


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Here you go: [1, 2] thanks') == [1, 2]
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_box_to_quad_scales_and_clamps():
    assert box_to_quad([100, 200, 500, 400], width=1000, height=2000) == [
        [200.0, 200.0], [400.0, 200.0], [400.0, 1000.0], [200.0, 1000.0],
    ]
    assert box_to_quad([-10, 0, 1200, 1000], 100, 100)[2] == [100.0, 100.0]


def test_render_prompt_contains_constraints_and_targets():
    components = [{"id": "c1", "type": "pillar", "quad": [[100, 0], [200, 0], [200, 500], [100, 500]]}]
    spec = {"style": "modern", "assignments": [
        {"target": "component:c1", "material_id": "slate", "color": None, "finish": "natural"},
        {"target": "type:wall", "material_id": "slate", "color": "#333333", "finish": ""},
    ], "keep_unchanged": ["window"]}
    prompt = build_render_prompt(spec, components, CATALOG, width=1000, height=1000)
    payload = json.loads(prompt.split("\n", 1)[1])

    assert any("camera angle" in c for c in payload["hard_constraints"])
    assert payload["changes"][0]["apply_to"] == "the pillar inside the box x 10%-20%, y 0%-50% of the image"
    assert payload["changes"][1]["apply_to"] == "every wall surface"
    assert payload["changes"][1]["material"] == "dark grey slate cladding"
    assert payload["keep_unchanged"] == ["window"]
