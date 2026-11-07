-- P6 — PDF → Excel Conversion Pipeline: extracted store.
-- Mirrors the schema created by src/extract.py (SQLite).
-- SAMPLE data only: 5 invoices, 20 lines, PKR 184,457.60.

CREATE TABLE invoices (
    invoice_no TEXT PRIMARY KEY,  -- e.g. INV-2026-001, as printed on the PDF
    date TEXT,                    -- e.g. 05 Oct 2026, as printed on the PDF
    buyer TEXT,                   -- buyer name + city, as printed on the PDF
    subtotal REAL,                -- sum of line amounts, as printed (PKR)
    tax REAL,                     -- sales tax, as printed on the PDF (PKR)
    total REAL                    -- subtotal + tax, as printed (PKR)
);

CREATE TABLE lines (
    invoice_no TEXT,              -- FK -> invoices.invoice_no
    description TEXT,             -- line-item description, as printed
    qty INTEGER,                  -- quantity
    unit_price REAL,              -- unit price in PKR
    amount REAL                   -- qty x unit_price, as printed (PKR)
);
