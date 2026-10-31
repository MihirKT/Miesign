from core.estimation import estimate, quantity, resolve_assignments

PAINT = {"id": "paint", "name": "Paint", "category": "Paint", "applies_to": ["wall", "pillar"],
         "rate_unit": "sqft", "qty_unit": "L", "coats": 2, "coverage_per_unit": 110, "wastage_pct": 5}
TILE = {"id": "tile", "name": "Tile", "category": "Tiles", "applies_to": ["wall"],
        "rate_unit": "sqft", "qty_unit": "pcs", "piece_sqft": 2, "wastage_pct": 10}
RAIL = {"id": "rail", "name": "Rail", "category": "Railing", "applies_to": ["railing"],
        "rate_unit": "rft", "qty_unit": "rft", "wastage_pct": 5}
CATALOG = {i["id"]: i for i in (PAINT, TILE, RAIL)}
RATES = {
    "paint": {"material_rate": 15, "labor_rate": 10, "source": "web"},
    "tile": {"material_rate": 70, "labor_rate": 40, "source": "estimated"},
    "rail": {"material_rate": 1000, "labor_rate": 200, "source": "override"},
}


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def comp(cid, ctype, quad):
    return {"id": cid, "type": ctype, "quad": quad, "floor": 0, "source": "ai", "confidence": None}


WALL = comp("w1", "wall", rect(0, 0, 100, 100))
WINDOW = comp("win", "window", rect(10, 10, 30, 30))
PILLAR = comp("p1", "pillar", rect(200, 0, 210, 100))
RAILING = comp("r1", "railing", rect(0, 200, 50, 210))
COMPONENTS = [WALL, WINDOW, PILLAR, RAILING]


def test_quantity_units():
    assert quantity(PAINT, 96) == 1.8
    assert quantity(TILE, 96) == 53
    assert quantity(RAIL, 5) == 5.2


def test_component_assignment_beats_type_assignment():
    spec = {"assignments": [
        {"target": "type:wall", "material_id": "paint"},
        {"target": "component:w1", "material_id": "tile"},
    ]}
    pairs = resolve_assignments(COMPONENTS, spec)
    assert [(c["id"], a["material_id"]) for c, a in pairs] == [("w1", "tile")]


def test_keep_unchanged_and_openings_are_skipped():
    spec = {"assignments": [{"target": "type:wall", "material_id": "paint"},
                            {"target": "type:window", "material_id": "paint"}],
            "keep_unchanged": ["wall"]}
    assert resolve_assignments(COMPONENTS, spec) == []


def test_estimate_lines_and_totals():
    spec = {"assignments": [
        {"target": "type:wall", "material_id": "paint"},
        {"target": "type:pillar", "material_id": "paint"},
        {"target": "type:railing", "material_id": "rail"},
    ]}
    result = estimate(COMPONENTS, spec, CATALOG, RATES, px_per_ft=10, scale_source="user")

    paint = next(line for line in result["lines"] if line["material_id"] == "paint")
    assert paint["measure"] == 136.0  # wall 96 + pillar 40
    assert paint["material_cost"] == round(136 * 1.05 * 15)
    assert paint["labor_cost"] == 1360
    assert sorted(paint["targets"]) == ["pillar×1", "wall×1"]

    rail = next(line for line in result["lines"] if line["material_id"] == "rail")
    assert rail["measure"] == 5.0
    assert rail["rate_source"] == "override"
    assert result["grand_total"] == sum(line["total"] for line in result["lines"])
    assert result["scale"] == {"px_per_ft": 10.0, "source": "user"}


def test_unsuitable_material_is_skipped_with_warning():
    spec = {"assignments": [{"target": "type:railing", "material_id": "tile"}]}
    result = estimate(COMPONENTS, spec, CATALOG, RATES, 10, "user")
    assert result["lines"] == []
    assert any("Tile" in w for w in result["warnings"])


def test_default_scale_is_flagged():
    result = estimate(COMPONENTS, {"assignments": []}, CATALOG, RATES, 10, "default")
    assert any("assumed" in a for a in result["assumptions"])
