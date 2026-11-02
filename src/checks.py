"""Data-quality checks for P6 — run after extract + build_excel.

Checks are independent of the extractor's database wherever possible:
PDF totals are re-read straight from PDF text here, then compared
against the workbook. Every check prints PASS/FAIL; exit code 1 on
any failure. Run:  python3 src/checks.py
"""
import re
import sys
from pathlib import Path

import pymupdf
from openpyxl import load_workbook

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
XLSX = BASE / "outputs" / "invoices_SAMPLE.xlsx"

fails = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name} {detail}")
    if not cond:
        fails.append(name)


def pdf_totals(path):
    """Re-read Subtotal/TOTAL lines from raw PDF text (no extractor)."""
    text = "\n".join(p.get_text() for p in pymupdf.open(path))
    sub = re.search(r"Subtotal\s+([\d,]+\.\d{2})", text)
    tot = re.search(r"TOTAL\s+([\d,]+\.\d{2})", text)
    return (float(sub.group(1).replace(",", "")),
            float(tot.group(1).replace(",", "")))


def main():
    wb = load_workbook(XLSX, data_only=False)
    lines = list(wb["Lines"].iter_rows(min_row=2, values_only=True))
    invoices = {r[0]: r for r in
                wb["Invoices"].iter_rows(min_row=2, values_only=True)}
    summary = list(wb["Summary"].iter_rows(min_row=2, values_only=True))

    check("workbook has 5 invoices", len(invoices) == 5, f"({len(invoices)})")
    check("workbook has 20 lines", len(lines) == 20, f"({len(lines)})")
    check("every line amount = qty x unit price",
          all(abs(r[6] - r[4] * r[5]) < 0.005 for r in lines))
    check("no PAID-stamp text leaked into lines",
          all("PAID" not in (r[3] or "") for r in lines))
    check("no header row leaked into lines",
          all(r[3] != "Item" for r in lines))
    check("all line invoice numbers exist in Invoices sheet",
          all(r[0] in invoices for r in lines))
    for inv_no, row in invoices.items():
        sub, tax, tot = row[3], row[4], row[5]
        check(f"{inv_no}: subtotal + tax = total",
              abs(round(sub + tax, 2) - tot) < 0.005, f"({sub}+{tax}={tot})")
        line_sum = round(sum(r[6] for r in lines if r[0] == inv_no), 2)
        check(f"{inv_no}: line items sum to PDF subtotal",
              abs(line_sum - sub) < 0.005, f"({line_sum} vs {sub})")
        pdf_sub, pdf_tot = pdf_totals(RAW / f"{inv_no}.pdf")
        check(f"{inv_no}: workbook totals match PDF text",
              abs(pdf_sub - sub) < 0.005 and abs(pdf_tot - tot) < 0.005,
              f"(PDF {pdf_sub}/{pdf_tot})")
    check("Summary sheet has a formula per invoice",
          all(str(r[2]).startswith("=SUMIF") for r in summary[:5]))
    check("Summary grand-total row present",
          summary[-1][0] == "GRAND TOTAL")
    grand = round(sum(r[5] for r in invoices.values()), 2)
    check("grand total across invoices", grand == 184457.60, f"({grand})")
    print(f"\n{len(fails)} failures" if fails else "\nall checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
