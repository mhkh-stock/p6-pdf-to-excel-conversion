"""Build the client deliverable workbook from data/processed/extracted.db.

Run:  python3 src/build_excel.py
Writes: outputs/invoices_SAMPLE.xlsx

Sheets: Lines (every line item, Excel Table, filters on),
Invoices (one row per invoice, totals as values read from the PDFs),
Summary (per-invoice line sums as live SUMIF formulas + grand totals),
Read-me (what the file is, SAMPLE label, how to re-run).
"""
import sqlite3
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.worksheet.table import Table, TableStyleInfo

BASE = Path(__file__).resolve().parents[1]
DB = BASE / "data" / "processed" / "extracted.db"
OUT = BASE / "outputs" / "invoices_SAMPLE.xlsx"


def main():
    con = sqlite3.connect(DB)
    invoices = con.execute(
        "SELECT invoice_no, date, buyer, subtotal, tax, total "
        "FROM invoices ORDER BY invoice_no").fetchall()
    lines = con.execute(
        "SELECT invoice_no, description, qty, unit_price, amount "
        "FROM lines ORDER BY invoice_no, rowid").fetchall()
    con.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Lines"
    ws.append(["Invoice No", "Date", "Buyer", "Item",
               "Qty", "Unit Price (PKR)", "Amount (PKR)"])
    inv_date = {i[0]: i[1] for i in invoices}
    inv_buyer = {i[0]: i[2] for i in invoices}
    for inv_no, desc, qty, price, amt in lines:
        ws.append([inv_no, inv_date[inv_no], inv_buyer[inv_no],
                   desc, qty, price, amt])
    ws.add_table(Table(displayName="Lines", ref=f"A1:G{len(lines) + 1}",
                       tableStyleInfo=TableStyleInfo(
                           name="TableStyleMedium9", showRowStripes=True)))
    for col, w in zip("ABCDEFG", [14, 13, 32, 44, 8, 16, 16]):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2, min_col=6, max_col=7):
        for c in row:
            c.number_format = "#,##0.00"

    inv_ws = wb.create_sheet("Invoices")
    inv_ws.append(["Invoice No", "Date", "Buyer",
                   "Subtotal (PKR)", "Tax 18% (PKR)", "Total (PKR)"])
    for row in invoices:
        inv_ws.append(list(row))
    for col, w in zip("ABCDEF", [14, 13, 32, 16, 14, 16]):
        inv_ws.column_dimensions[col].width = w
    for row in inv_ws.iter_rows(min_row=2, min_col=4, max_col=6):
        for c in row:
            c.number_format = "#,##0.00"

    s = wb.create_sheet("Summary")
    s.append(["Invoice No", "Lines", "Line-sum (PKR, formula)",
              "PDF total (PKR)", "Match?"])
    for i, row in enumerate(invoices, start=2):
        inv_no = row[0]
        s.append([inv_no,
                  f"=COUNTIF(Lines!A:A,A{i})",
                  f"=SUMIF(Lines!A:A,A{i},Lines!G:G)",
                  row[5],
                  f"=IF(ROUND(C{i}+ROUND(C{i}*0.18,2),2)=D{i},\"OK\",\"CHECK\")"])
        # line-sum is the subtotal; PDF total = subtotal + rounded 18% tax
    n = len(invoices) + 1
    s.append(["GRAND TOTAL", f"=SUM(B2:B{n})", f"=SUM(C2:C{n})",
              f"=SUM(D2:D{n})", ""])
    for col, w in zip("ABCDE", [14, 8, 22, 16, 10]):
        s.column_dimensions[col].width = w
    for row in s.iter_rows(min_row=2, min_col=3, max_col=4):
        for c in row:
            c.number_format = "#,##0.00"

    r = wb.create_sheet("Read-me")
    r.append(["PDF → Excel Conversion Pipeline — SAMPLE delivery"])
    r["A1"].font = Font(bold=True, size=14)
    notes = [
        "Supplier: Karachi Office Supplies (fictional). Buyers are fictional.",
        "Source: 5 invoice PDFs in data/raw/, converted by src/extract.py",
        "  (PyMuPDF word-box parsing — no manual typing, no re-keying).",
        "Lines sheet: every line item from every invoice, as extracted.",
        "Invoices sheet: subtotal / tax / total exactly as printed on each PDF.",
        "Summary sheet: line-sums are live SUMIF formulas; Match? checks",
        "  line-sum x 1.18 against the PDF total (all must read OK).",
        "SAMPLE data: this workbook demonstrates the service. A real order",
        "  runs the same pipeline on the client's own PDFs.",
        "Re-run: python3 src/extract.py && python3 src/build_excel.py",
        "Verify: python3 src/checks.py",
    ]
    for note in notes:
        r.append([note])
    r.column_dimensions["A"].width = 90

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT} — {len(lines)} lines, {len(invoices)} invoices")


if __name__ == "__main__":
    main()
