"""Tests PDF generation and INR formatting.

Miesign · Author: Mihir Kapildev Tiwari
"""

from core.managers.report import build_pdf, inr

ESTIMATE = {
    "scale": {"px_per_ft": 20, "source": "default"},
    "lines": [{"category": "Paint", "name": "Exterior emulsion paint", "material_id": "exterior_emulsion",
               "targets": ["wall×2"], "measure": 812.4, "rate_unit": "sqft", "quantity": 15.5, "qty_unit": "L",
               "wastage_pct": 5, "material_rate": 16, "labor_rate": 10, "rate_source": "web",
               "material_cost": 13648, "labor_cost": 8124, "total": 21772}],
    "grand_total": 21772,
    "assumptions": ["Only the visible facade is measured."],
    "warnings": [],
    "location": {"state": "Maharashtra", "city": "Pune"},
}


def test_inr_grouping():
    assert inr(999) == "Rs 999"
    assert inr(1000) == "Rs 1,000"
    assert inr(184500) == "Rs 1,84,500"
    assert inr(12345678) == "Rs 1,23,45,678"


def test_pdf_bytes():
    pdf = build_pdf("My house", "Modern slate", ESTIMATE, ["Exterior emulsion paint on wall"], None, None)
    assert pdf.startswith(b"%PDF")


def test_inr_edges():
    assert inr(0) == "Rs 0"
    assert inr(-0.2) == "Rs 0"
    assert inr(2.5) == "Rs 3"
    assert inr(99999) == "Rs 99,999"
    assert inr(100000) == "Rs 1,00,000"
    assert inr(10000000) == "Rs 1,00,00,000"


def _png(path, w, h):
    from PIL import Image
    Image.new("RGB", (w, h), "red").save(path)
    return str(path)


def test_pdf_escapes_markup():
    est = {**ESTIMATE, "warnings": ["Check <b>unclosed"], "assumptions": ["Tom & Jerry"]}
    pdf = build_pdf("Sharma & Sons <Villa>", "A & <B>", est, ["Paint <x> & y"], None, None)
    assert pdf.startswith(b"%PDF")


def test_pdf_missing_original_real_render(tmp_path):
    render = _png(tmp_path / "r.png", 40, 30)
    pdf = build_pdf("H", "D", ESTIMATE, [], str(tmp_path / "nope.png"), render)
    assert pdf.startswith(b"%PDF")


def test_pdf_very_tall_image(tmp_path):
    tall = _png(tmp_path / "t.png", 100, 2000)
    assert build_pdf("H", "D", ESTIMATE, [], tall, tall).startswith(b"%PDF")


def test_category_rows_subtotals():
    from core.managers.report import category_rows
    mk = lambda c, m, l: {"category": c, "material_cost": m, "labor_cost": l, "total": m + l}
    lines = [mk("Paint", 10, 5), mk("Tiles", 100, 50), mk("Paint", 20, 10)]
    groups = category_rows(lines)
    assert [g[0] for g in groups] == ["Paint", "Tiles"]
    assert len(groups[0][1]) == 2
    assert groups[0][2] == {"material": 30, "labor": 15, "total": 45}
    assert groups[1][2] == {"material": 100, "labor": 50, "total": 150}
