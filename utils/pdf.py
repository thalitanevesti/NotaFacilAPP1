from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from PIL import Image
import datetime

def brl(v):
    # Formata número em BRL: R$ 1.234,56
    try:
        s = f"{float(v):,.2f}"
    except Exception:
        s = "0.00"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def build_pdf(
    company_name: str,
    company_doc: str,
    company_address: str,
    client_name: str,
    client_doc: str,
    doc_number: str,
    issue_date: str,
    description: str,
    value: float,
    logo_bytes: bytes | None = None,
) -> bytes:
    buffer = BytesIO()
    w, h = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle("Nota/Recibo")

    margin = 18 * mm

    # Header box
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(1)
    c.rect(margin, h - 60 * mm, w - 2 * margin, 45 * mm, stroke=1, fill=0)

    # Logo (left)
    x_logo = margin + 5 * mm
    y_logo = h - 25 * mm
    if logo_bytes:
        try:
            img = Image.open(BytesIO(logo_bytes)).convert("RGBA")
            # Resize to fit 40x40mm
            max_w = 40 * mm
            max_h = 40 * mm
            ratio = min(max_w / img.width, max_h / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size)
            c.drawImage(ImageReader(img), x_logo, h - 55 * mm, width=new_size[0], height=new_size[1], mask='auto')
        except Exception:
            pass

    # Company info
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin + 50 * mm, h - 25 * mm, company_name or "Sua Empresa")
    c.setFont("Helvetica", 10)
    c.drawString(margin + 50 * mm, h - 32 * mm, f"Documento: {company_doc or '-'}")
    c.drawString(margin + 50 * mm, h - 38 * mm, f"Endereço: {company_address or '-'}")

    # Right header: doc number & date
    c.setFont("Helvetica", 10)
    c.drawRightString(w - margin - 5 * mm, h - 25 * mm, f"Nº: {doc_number or '-'}")
    c.drawRightString(w - margin - 5 * mm, h - 32 * mm, f"Data: {issue_date or datetime.date.today().isoformat()}")

    # Client box
    c.rect(margin, h - 90 * mm, w - 2 * margin, 25 * mm, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin + 5 * mm, h - 78 * mm, "Dados do Cliente")
    c.setFont("Helvetica", 10)
    c.drawString(margin + 5 * mm, h - 85 * mm, f"Nome/Razão Social: {client_name or '-'}")
    c.drawString(margin + 5 * mm, h - 91 * mm, f"CPF/CNPJ: {client_doc or '-'}")

    # Description/value box
    c.rect(margin, h - 180 * mm, w - 2 * margin, 85 * mm, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin + 5 * mm, h - 100 * mm, "Descrição do Serviço/Produto")
    c.setFont("Helvetica", 10)

    # Multi-line description wrap
    from textwrap import wrap
    max_chars = 90
    y_text = h - 108 * mm
    for line in wrap(description or "-", max_chars):
        c.drawString(margin + 5 * mm, y_text, line)
        y_text -= 6 * mm

    # Value box
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w - margin - 5 * mm, h - 165 * mm, "Valor")
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(w - margin - 5 * mm, h - 175 * mm, brl(value))

    # Footer / disclaimer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(margin, 20 * mm, "Este documento é um recibo/nota simples e NÃO substitui NF-e/NFS-e oficial.")
    c.drawRightString(w - margin, 20 * mm, "Gerado por Nota Fácil Lite")

    c.showPage()
    c.save()
    return buffer.getvalue()
