from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.catalog import load_catalog
from core.managers import estimates
from core.managers.projects import primary_photo
from core.models import Project

IMAGE_WIDTH = 85 * mm
INK = colors.HexColor("#1f2a37")
RULE = colors.HexColor("#d5dbe3")
DISCLAIMER = ("Advisory estimate generated from one photo. Areas are approximate and rates are averages; "
              "confirm measurements and prices with your contractor before work begins.")


def inr(amount):
    digits = str(int(round(abs(amount))))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return ("-" if amount < 0 else "") + "Rs " + digits


def _image(path):
    img = Image(path)
    img.drawHeight = IMAGE_WIDTH * img.imageHeight / img.imageWidth
    img.drawWidth = IMAGE_WIDTH
    return img


def build_pdf(project_name, design_name, estimate, materials, original_path, render_path):
    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm, title=f"{project_name} - renovation estimate")
    loc = estimate.get("location") or {}
    where = ", ".join(v for v in (loc.get("city"), loc.get("state")) if v) or "Location not set"
    story = [
        Paragraph(f"{project_name}: exterior renovation estimate", styles["Title"]),
        Paragraph(f"Design: {design_name} &middot; {where} &middot; "
                  f"{datetime.now(timezone.utc):%d %b %Y}", styles["Normal"]),
        Spacer(1, 6 * mm),
    ]
    images = [[_image(p) if p else Paragraph("No image", styles["Normal"]) for p in (original_path, render_path)]]
    if original_path or render_path:
        story += [Table([["Original", "Redesigned"]] + images, colWidths=[IMAGE_WIDTH + 4 * mm] * 2),
                  Spacer(1, 6 * mm)]

    story.append(Paragraph("Selected materials", styles["Heading2"]))
    story += [Paragraph(f"&bull; {m}", styles["Normal"]) for m in materials] or [Paragraph("None", styles["Normal"])]
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Quantities and cost", styles["Heading2"]))
    rows = [["Item", "Area / length", "Quantity", "Rate (mat + lab)", "Material", "Labour", "Total"]]
    for line in estimate["lines"]:
        rows.append([
            Paragraph(f"{line['name']}<br/><font size=7>{', '.join(line['targets'])} &middot; "
                      f"{line['rate_source']}</font>", styles["BodyText"]),
            f"{line['measure']} {line['rate_unit']}",
            f"{line['quantity']} {line['qty_unit']}",
            f"{line['material_rate']} + {line['labor_rate']} /{line['rate_unit']}",
            inr(line["material_cost"]), inr(line["labor_cost"]), inr(line["total"]),
        ])
    rows.append(["Grand total", "", "", "", "", "", inr(estimate["grand_total"])])
    table = Table(rows, colWidths=[48 * mm, 22 * mm, 20 * mm, 28 * mm, 20 * mm, 20 * mm, 22 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, INK),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, RULE),
        ("LINEABOVE", (0, -1), (-1, -1), 1, INK),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [table, Spacer(1, 6 * mm), Paragraph("Assumptions", styles["Heading2"])]
    story += [Paragraph(f"&bull; {a}", styles["Normal"]) for a in estimate["assumptions"] + estimate["warnings"]]
    story += [Spacer(1, 6 * mm), Paragraph(DISCLAIMER, styles["Italic"])]
    doc.build(story)
    return buf.getvalue()


def for_design(design):
    project = Project.objects.get(id=design.project_id)
    photo = primary_photo(project)
    catalog = load_catalog()
    materials = [
        f"{catalog[a['material_id']]['name']} on {a['target'].split(':', 1)[1].replace('_', ' ')}"
        + (f" ({a['color']})" if a.get("color") else "")
        for a in design.spec.get("assignments", []) if a["material_id"] in catalog
    ]
    render_path = design.render_file.path if design.render_file else None
    return build_pdf(project.name, design.name, estimates.for_design(design), materials,
                     photo.file.path, render_path)
