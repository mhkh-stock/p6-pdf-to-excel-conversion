"""Generate the SAMPLE invoice PDFs that the P6 pipeline converts.

Fictional supplier, fictional buyers, SAMPLE data — these PDFs exist
so the extractor has realistic input to prove itself on. Run:

    python3 src/make_sample_pdfs.py

Writes 5 PDFs to data/raw/. Totals are computed here and printed
on the PDF itself (subtotal / 18% sales tax / total) — the extractor
reads them back from the PDF text, it never sees this file's numbers.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle)

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "raw"

SUPPLIER = "Karachi Office Supplies"
SUPPLIER_ADDR = "Shop 12, Saddar Market, Karachi, Pakistan"

# (invoice_no, date, buyer, [(description, qty, unit_price)], paid_stamp)
INVOICES = [
    ("INV-2026-001", "05 Oct 2026", "Al-Noor Book Depot, Hyderabad", [
        ("A4 Paper Ream (500 sheets)", 10, 850.00),
        ("Ball Pen Blue (box of 50)", 8, 420.00),
        ("Spiral Notebook A5", 25, 180.00),
        ("Stapler Heavy Duty", 4, 1250.00),
    ], False),
    ("INV-2026-002", "09 Oct 2026", "City School Stationery Store, Lahore", [
        ("Whiteboard Marker Set (8 colours, refillable)", 12, 950.00),
        ("File Folder Plastic A4 (pack of 10)", 20, 310.00),
        ("Geometry Box Student Edition", 30, 240.00),
    ], False),
    ("INV-2026-003", "14 Oct 2026", "Bright Future Academy, Karachi", [
        ("Printer Toner Cartridge HP 12A Compatible", 3, 6800.00),
        ("A3 Chart Paper Pack (100 sheets)", 6, 720.00),
        ("Crayons Wax 24 Shades", 40, 195.00),
        ("Glue Stick Large", 24, 120.00),
        ("Delivery Charges - City Courier", 1, 500.00),
    ], True),  # carries a PAID stamp the extractor must ignore
    ("INV-2026-004", "19 Oct 2026", "Al-Noor Book Depot, Hyderabad", [
        ("Exercise Book 200 Pages (bundle of 12)", 60, 540.00),
        ("Pencil HB (box of 100)", 15, 380.00),
    ], False),
    ("INV-2026-005", "26 Oct 2026", "Home Office Solutions, Islamabad", [
        ("Desk Organizer Wooden 5 Slot", 5, 2100.00),
        ("Sticky Notes 3x3 (pack of 12 pads)", 18, 260.00),
        ("Paper Clips Assorted (box of 200)", 10, 150.00),
        ("Highlighter Set Neon (6 pens)", 14, 480.00),
        ("Calculator Scientific 12 Digit", 7, 1450.00),
        ("Envelope Brown A4 (pack of 50)", 9, 290.00),
    ], False),
]


def money(v):
    return f"{v:,.2f}"


def build(inv_no, date, buyer, items, paid):
    path = OUT / f"{inv_no}.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"<b>{SUPPLIER}</b>", styles["Title"]),
             Paragraph(SUPPLIER_ADDR, styles["Normal"]),
             Spacer(1, 6 * mm),
             Paragraph(f"<b>Invoice: {inv_no}</b>", styles["Heading2"]),
             Paragraph(f"Date: {date}", styles["Normal"]),
             Paragraph(f"Bill to: {buyer}", styles["Normal"]),
             Spacer(1, 4 * mm)]
    rows = [["Item", "Qty", "Unit Price (PKR)", "Amount (PKR)"]]
    subtotal = 0.0
    for desc, qty, price in items:
        amt = qty * price
        subtotal += amt
        rows.append([desc, str(qty), money(price), money(amt)])
    tax = round(subtotal * 0.18, 2)
    total = round(subtotal + tax, 2)
    rows.append(["", "", "Subtotal", money(subtotal)])
    rows.append(["", "", "Sales Tax (18%)", money(tax)])
    rows.append(["", "", "TOTAL", money(total)])
    t = Table(rows, colWidths=[78 * mm, 16 * mm, 32 * mm, 32 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dddddd")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Thank you for your business. Payment due within 14 days.",
                           styles["Normal"]))
    if paid:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("<b>PAID - Thank you</b>", styles["Heading2"]))
    doc.build(story)
    print(f"{inv_no}: {len(items)} items, subtotal {money(subtotal)}, "
          f"tax {money(tax)}, total {money(total)} -> {path.name}")
    return inv_no, len(items), subtotal, tax, total


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for inv in INVOICES:
        build(*inv)


if __name__ == "__main__":
    main()
