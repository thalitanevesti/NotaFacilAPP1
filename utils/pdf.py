from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, black, HexColor
from reportlab.lib.utils import ImageReader

BRAND = "Nota Fácil Lite — Mibit"
WATERMARK_OPACITY = 0.06
PRIMARY = HexColor("#6b72ff")

def _parse_money_br(v):
    if v is None: return 0.0
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip()
    if not s: return 0.0
    s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except: return 0.0

def _fmt_money_br(n: float) -> str:
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def _kv(c, x, y, k, v, key_w=36*mm, lh=6.8*mm):
    c.setFillColor(black); c.setFont("Helvetica-Bold", 10); c.drawString(x, y, k)
    c.setFont("Helvetica", 10); c.drawString(x + key_w, y, v or "")
    return y - lh

def gerar_pdf(dados, logo_bytes=None):
    # Normaliza dados (form plano)
    empresa = {
        "nome": dados.get("company_name", ""),
        "doc":  dados.get("company_doc", ""),
        "end":  dados.get("company_address", ""),
    }
    cliente = {
        "nome": dados.get("client_name", ""),
        "doc":  dados.get("client_doc", ""),
    }
    doc_number = dados.get("doc_number", "") or ""
    issue_date = dados.get("issue_date", "") or ""
    desc       = (dados.get("description") or "").strip() or "Serviço/Produto"
    valor      = _parse_money_br(dados.get("value"))

    # Data → DD/MM/AAAA
    if issue_date:
        try: issue_date_fmt = datetime.strptime(issue_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except: issue_date_fmt = issue_date
    else:
        issue_date_fmt = ""

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Marca d'água
    c.saveState()
    c.translate(w/2, h/2); c.rotate(45)
    c.setFont("Helvetica-Bold", 52)
    c.setFillColor(Color(0,0,0,alpha=WATERMARK_OPACITY))
    c.drawCentredString(0, 0, BRAND)
    c.restoreState()

    # Cabeçalho (barra)
    c.setFillColor(PRIMARY); c.rect(0, h-26*mm, w, 26*mm, fill=1, stroke=0)
    c.setFillColorRGB(1,1,1); c.setFont("Helvetica-Bold", 18)
    c.drawString(20*mm, h-16*mm, "RECIBO / NOTA")
    c.setFont("Helvetica", 10); c.drawRightString(w-20*mm, h-12*mm, BRAND)

    y = h-34*mm
    x_left = 20*mm

    # Logo (opcional do cliente)
    if logo_bytes:
        try:
            img = ImageReader(BytesIO(logo_bytes))
            max_w, max_h = 36*mm, 22*mm
            iw, ih = img.getSize(); ratio = min(max_w/iw, max_h/ih)
            dw, dh = iw*ratio, ih*ratio
            c.drawImage(img, x_left, y-dh+4*mm, width=dw, height=dh, mask='auto')
            x_left = x_left + max_w + 6*mm
        except: pass

    # Empresa
    c.setFillColor(black); c.setFont("Helvetica-Bold", 12)
    c.drawString(x_left, y, "Empresa")
    y -= 8*mm; c.setFont("Helvetica", 10)
    y = _kv(c, x_left, y, "Nome/Razão:", empresa["nome"])
    y = _kv(c, x_left, y, "CNPJ/CPF:",  empresa["doc"])
    y = _kv(c, x_left, y, "Endereço:",  empresa["end"])

    # Cliente
    y -= 3*mm; c.setFont("Helvetica-Bold", 12); c.drawString(20*mm, y, "Cliente")
    y -= 8*mm; c.setFont("Helvetica", 10)
    y = _kv(c, 20*mm, y, "Nome/Razão:", cliente["nome"])
    y = _kv(c, 20*mm, y, "CPF/CNPJ:",  cliente["doc"])

    # Documento
    y -= 3*mm; c.setFont("Helvetica-Bold", 12); c.drawString(20*mm, y, "Documento")
    y -= 8*mm; c.setFont("Helvetica", 10)
    y = _kv(c, 20*mm, y, "Número:", doc_number)
    y = _kv(c, 20*mm, y, "Data:",   issue_date_fmt)

    # Itens (1 linha simples)
    y -= 3*mm; c.setFont("Helvetica-Bold", 12); c.drawString(20*mm, y, "Itens")
    y -= 8*mm; c.setFont("Helvetica", 10)
    c.drawString(20*mm, y, f"- {desc} | qtd: 1 | {_fmt_money_br(valor)} | Subtotal: {_fmt_money_br(valor)}")
    y -= 10*mm

    # Total
    c.setFont("Helvetica-Bold", 13); c.setFillColor(PRIMARY)
    c.drawString(20*mm, y, f"TOTAL: {_fmt_money_br(valor)}"); c.setFillColor(black)
    y -= 12*mm

    # Rodapé
    c.setFont("Helvetica", 9)
    c.drawString(20*mm, y, "Este documento é um recibo/nota simples e não substitui NF-e.")
    c.showPage(); c.save(); buf.seek(0)
    return buf
