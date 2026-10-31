"""Tests the geometry helpers: areas, point-in-polygon, scale and overlap warnings.

Miesign · Author: Mihir Kapildev Tiwari
"""

import pytest

from core.estimation import (
    area_sqft, default_scale, measure, point_in_polygon, polygon_area_px,
    scale_from_component, walls_overlap_warnings,
)


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def comp(cid, ctype, quad):
    return {"id": cid, "type": ctype, "quad": quad, "floor": 0, "source": "ai", "confidence": None}


def test_rect_area():
    assert polygon_area_px(rect(0, 0, 100, 50)) == 5000
    assert area_sqft(rect(0, 0, 100, 100), 10) == pytest.approx(100)


def test_degenerate_quad_is_zero():
    assert area_sqft([[5, 5], [5, 5], [5, 5], [5, 5]], 10) == 0
    assert area_sqft(rect(0, 0, 100, 100), 0) == 0


def test_point_in_polygon():
    square = rect(0, 0, 10, 10)
    assert point_in_polygon((5, 5), square)
    assert not point_in_polygon((15, 5), square)


def test_wall_net_subtracts_contained_openings_only():
    wall = comp("w", "wall", rect(0, 0, 100, 100))
    inside = comp("a", "window", rect(10, 10, 30, 30))
    outside = comp("b", "window", rect(200, 200, 220, 220))
    value = measure(wall, [wall, inside, outside], px_per_ft=10, rate_unit="sqft")
    assert value == pytest.approx(96)


def test_pillar_counts_four_faces():
    pillar = comp("p", "pillar", rect(0, 0, 10, 100))
    assert measure(pillar, [pillar], 10, "sqft") == pytest.approx(40)


def test_rft_uses_width():
    railing = comp("r", "railing", rect(0, 0, 50, 10))
    assert measure(railing, [railing], 10, "rft") == pytest.approx(5)


def test_scale_from_component():
    assert scale_from_component(rect(0, 0, 30, 140), 7) == pytest.approx(20)
    with pytest.raises(ValueError):
        scale_from_component(rect(0, 0, 30, 140), 0)


def test_default_scale_prefers_door_then_window_then_image():
    door = comp("d", "door", rect(0, 0, 30, 140))
    window = comp("w", "window", rect(0, 0, 40, 80))
    assert default_scale([door, window], 1000) == pytest.approx(20)
    assert default_scale([window], 1000) == pytest.approx(20)
    assert default_scale([], 1000) == pytest.approx(50)


def test_overlapping_walls_warn():
    a = comp("a", "wall", rect(0, 0, 100, 100))
    b = comp("b", "wall", rect(50, 0, 150, 100))
    c = comp("c", "wall", rect(300, 0, 400, 100))
    assert len(walls_overlap_warnings([a, b])) == 1
    assert walls_overlap_warnings([a, c]) == []
