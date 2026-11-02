"""Extract invoice line items + totals from the SAMPLE PDFs in data/raw/.

Method: PyMuPDF word boxes, grouped into rows by vertical position.
A row whose last three tokens are (integer, money, money) is a line
item; rows starting with Subtotal / Sales Tax / TOTAL are totals.
Everything else (headers, thank-you note, PAID stamp) is ignored by
construction — the PAID stamp on INV-2026-003 is the test for that.

Run:  python3 src/extract.py
Writes: data/processed/extracted.db (invoices + lines tables)
Prints: one line per invoice with counts and totals.
"""
import re
import sqlite3
from pathlib import Path

import pymupdf

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
DB = BASE / "data" / "processed" / "extracted.db"

MONEY = re.compile(r"^\d{1,3}(,\d{3})*(\.\d{2})$")
INT = re.compile(r"^\d+$")
INV_NO = re.compile(r"INV-\d{4}-\d{3}")
DATE = re.compile(r"\d{2} [A-Z][a-z]{2} \d{4}")


def rows_of(page):
    """Group word boxes into text rows, left to right."""
    buckets = {}
    for x0, y0, _x1, _y1, word, _b, _l, _n in page.get_text("words"):
        buckets.setdefault(round(y0 / 3), []).append((x0, word))
    return [" ".join(w for _x, w in sorted(bucket))
            for _y, bucket in sorted(buckets.items())]


def parse_money(tok):
    return float(tok.replace(",", "")) if MONEY.match(tok) else None


def parse_pdf(path):
    doc = pymupdf.open(path)
    inv_no = date = buyer = None
    items, totals = [], {}
    for page in doc:
        for row in rows_of(page):
            toks = row.split()
            if not toks:
                continue
            m = INV_NO.search(row)
            if m and inv_no is None:
                inv_no = m.group(0)
            if row.startswith("Date:") and date is None:
                d = DATE.search(row)
                date = d.group(0) if d else None
            if row.startswith("Bill to:") and buyer is None:
                buyer = row[len("Bill to:"):].strip()
            if toks[0] == "Subtotal" and len(toks) == 2:
                totals["subtotal"] = parse_money(toks[1])
            elif toks[0] == "TOTAL" and len(toks) == 2:
                totals["total"] = parse_money(toks[1])
            elif toks[0] == "Sales" and toks[1] == "Tax":
                totals["tax"] = parse_money(toks[-1])
            elif (len(toks) >= 4 and INT.match(toks[-3])
                    and parse_money(toks[-2]) is not None
                    and parse_money(toks[-1]) is not None):
                items.append({
                    "description": " ".join(toks[:-3]),
                    "qty": int(toks[-3]),
                    "unit_price": parse_money(toks[-2]),
                    "amount": parse_money(toks[-1]),
                })
    if not (inv_no and items and len(totals) == 3):
        raise ValueError(f"{path.name}: incomplete parse "
                         f"(inv={inv_no}, items={len(items)}, totals={totals})")
    return {"invoice_no": inv_no, "date": date, "buyer": buyer,
            "items": items, **totals}


def main():
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript("""
        CREATE TABLE invoices (
            invoice_no TEXT PRIMARY KEY, date TEXT, buyer TEXT,
            subtotal REAL, tax REAL, total REAL);
        CREATE TABLE lines (
            invoice_no TEXT, description TEXT, qty INTEGER,
            unit_price REAL, amount REAL);
    """)
    for path in sorted(RAW.glob("*.pdf")):
        inv = parse_pdf(path)
        con.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?)",
                    (inv["invoice_no"], inv["date"], inv["buyer"],
                     inv["subtotal"], inv["tax"], inv["total"]))
        con.executemany("INSERT INTO lines VALUES (?,?,?,?,?)",
                        [(inv["invoice_no"], it["description"], it["qty"],
                          it["unit_price"], it["amount"])
                         for it in inv["items"]])
        print(f"{inv['invoice_no']}: {len(inv['items'])} items, "
              f"subtotal {inv['subtotal']:,.2f}, tax {inv['tax']:,.2f}, "
              f"total {inv['total']:,.2f}")
    con.commit()
    n_inv, n_lines = con.execute(
        "SELECT COUNT(*) FROM invoices").fetchone()[0], con.execute(
        "SELECT COUNT(*) FROM lines").fetchone()[0]
    con.close()
    print(f"wrote {DB} — {n_inv} invoices, {n_lines} lines")


if __name__ == "__main__":
    main()
