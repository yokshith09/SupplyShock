"""Draft purchase order PDF (reportlab). Output dir: PO_OUTPUT_DIR (default out/po). Always marked DRAFT."""
import os
from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]


def output_dir() -> Path:
    d = Path(os.getenv("PO_OUTPUT_DIR", str(ROOT / "out" / "po")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def next_po_number(directory: Path | None = None) -> str:
    d = directory or output_dir()
    n = len(list(d.glob("PO-*.pdf"))) + 1
    return f"PO-{date.today().year}-{n:04d}"


def make_po(company: str, supplier: dict, material: dict, qty: int, unit_price_inr: float,
            need_by: str | None = None) -> tuple[str, Path]:
    d = output_dir()
    po = next_po_number(d)
    path = d / f"{po}.pdf"
    total = qty * unit_price_inr
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    y = h - 25 * mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, f"PURCHASE ORDER {po}  (DRAFT)")
    c.setFont("Helvetica", 10)
    rows = [
        f"Date: {date.today().isoformat()}",
        f"Buyer: {company}",
        "",
        f"Supplier: {supplier.get('name', supplier.get('id', '?'))} ({supplier.get('id', '?')})",
        f"Location: {supplier.get('city', '')} {supplier.get('country', '')}".strip(),
        f"Email: {supplier.get('email', '')}",
        "",
        f"Item: {material.get('name', material.get('id', '?'))} ({material.get('id', '?')})",
        f"Quantity: {qty} {material.get('unit', 'pcs')}",
        f"Unit price (INR): {unit_price_inr:,.2f}",
        f"Total (INR): {total:,.2f}",
        f"Need by: {need_by or 'to be confirmed'}",
        "",
        "This is a DRAFT for review. It is not binding until approved and issued by procurement.",
    ]
    y -= 12 * mm
    for line in rows:
        c.drawString(20 * mm, y, line)
        y -= 7 * mm
    c.showPage()
    c.save()
    return po, path
