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
