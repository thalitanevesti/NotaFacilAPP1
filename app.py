import os
from datetime import datetime, timedelta
from io import BytesIO
import ssl
import smtplib
from email.message import EmailMessage

from flask import Flask, render_template, request, send_file, abort, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import jwt

from utils.pdf import build_pdf

# ======================================================
# Configuração base
# ======================================================
load_dotenv()
app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB para upload do logo
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() == "true"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")

# Limiter precisa do app já criado
limiter = Limiter(get_remote_address, app=app, default_limits=["30 per minute"])


def _verify_token():
    """Verifica token JWT da querystring (?t=...). Retorna payload ou None."""
    if DISABLE_AUTH:
        return {"email": "dev@local", "dev": True}
    token = request.args.get("t")
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except Exception:
        return None


# ======================================================
# Healthcheck
# ======================================================
@app.get("/health")
def health():
    return {"status": "ok"}


# ======================================================
# Página principal
# ======================================================
@app.get("/")
@limiter.limit("60/minute")
def index():
    payload = _verify_token()
    if payload is None:
        abort(401, description="Acesso não autorizado. Token ausente ou inválido.")
    return render_template("index.html", payload=payload)


# ======================================================
# Geração de PDF
# ======================================================
@app.post("/generate")
@limiter.limit("30/minute")
def generate_pdf():
    payload = _verify_token()
    if payload is None:
        abort(401, description="Acesso não autorizado. Token ausente ou inválido.")

    # Coleta dados do formulário
    company_name = request.form.get("company_name", "").strip()
    company_doc = request.form.get("company_doc", "").strip()
    company_address = request.form.get("company_address", "").strip()

    client_name = request.form.get("client_name", "").strip()
    client_doc = request.form.get("client_doc", "").strip()

    doc_number = request.form.get("doc_number", "").strip()
    issue_date = request.form.get("issue_date", "").strip() or datetime.now().strftime("%Y-%m-%d")
    description = request.form.get("description", "").strip()
    value = request.form.get("value", "0").replace(",", ".").strip()

    logo_file = request.files.get("logo")

    # Sanitização simples
    try:
        value_float = float(value)
        if value_float < 0:
            value_float = 0.0
    except Exception:
        value_float = 0.0

    logo_bytes = None
    if logo_file and logo_file.filename:
        # Verifica extensão
        allowed = {"png", "jpg", "jpeg"}
        ext = logo_file.filename.rsplit(".", 1)[-1].lower()
        if ext not in allowed:
            abort(400, description="Logo deve ser PNG/JPG.")
        logo_bytes = logo_file.read()

    pdf_bytes = build_pdf(
        company_name=company_name,
        company_doc=company_doc,
        company_address=company_address,
        client_name=client_name,
        client_doc=client_doc,
        doc_number=doc_number,
        issue_date=issue_date,
        description=description,
        value=value_float,
        logo_bytes=logo_bytes,
    )

    filename = f"nota_{doc_number or datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


# ======================================================
# WEBHOOK HOTMART (corrigido)
# ======================================================
def send_access_email(to_email: str, access_link: str) -> None:
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    FROM_EMAIL = os.getenv("FROM_EMAIL", os.getenv("SMTP_USER", "no-reply@seuapp.com"))

    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS]):
        raise RuntimeError("SMTP não configurado")

    msg = EmailMessage()
    msg["Subject"] = "Seu acesso ao Nota Fácil Lite"
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    body = (
        "Olá!\n\n"
        "Obrigado pela compra. Acesse seu app por este link:\n"
        f"{access_link}\n\n"
        "Guarde este e-mail. Qualquer dúvida, responda por aqui.\n"
    )
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls(context=context)
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)


def _extract_hotmart_fields(payload: dict):
    """
    Extrai os campos principais do payload v2.0.0 da Hotmart.
    Exemplo esperado:
    {
      "event": "PURCHASE_APPROVED",
      "version": "2.0.0",
      "data": {
        "buyer": {"email": "..."},
        "purchase": {"status": "APPROVED", "transaction": "HP..."}
      }
    }
    """
    event = payload.get("event") or ""
    data = payload.get("data") or {}

    buyer = data.get("buyer") or {}
    email = (buyer.get("email") or "").strip().lower()

    purchase = data.get("purchase") or {}
    status = (purchase.get("status") or "").upper()
    transaction = purchase.get("transaction") or purchase.get("transaction_id") or ""

    # Fallback para testes antigos/simplificados
    if not email:
        email = (payload.get("buyer_email") or payload.get("email") or "").strip().lower()
    if not status:
        status = (payload.get("status") or payload.get("purchase_status") or "").upper()

    return event, email, status, transaction


@app.post("/webhook/hotmart")
def hotmart_webhook():
    # 1) Valida segredo
    expected = os.getenv("WEBHOOK_SECRET")
    got = request.headers.get("x-hotmart-secret")
    if expected and expected != got:
        return jsonify({"ok": False, "error": "invalid signature"}), 401

    # 2) Lê JSON
    payload = request.get_json(silent=True) or (request.form.to_dict() if request.form else {})
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "invalid payload"}), 400

    event, buyer_email, status, transaction = _extract_hotmart_fields(payload)

    if not buyer_email:
        return jsonify({"ok": False, "error": "missing email"}), 400

    # 3) Só libera em aprovado/pago
    if status not in {"APPROVED", "PAID"}:
        return jsonify({"ok": True, "ignored": status or event}), 200

    # 4) Gera token JWT (mesma lógica usada no app)
    exp = datetime.utcnow() + timedelta(days=365)
    token = jwt.encode({"email": buyer_email, "exp": exp}, JWT_SECRET, algorithm="HS256")

    app_url = os.getenv("APP_URL", "https://nota-facil-lite.onrender.com")
    access_link = f"{app_url}/?t={token}"

    # 5) Envia e-mail com link de acesso
    try:
        send_access_email(buyer_email, access_link)
    except Exception as e:
        # Para a Hotmart reenviar em caso de falha de e-mail, retorne 500
        return jsonify({"ok": False, "error": f"email fail: {e}"}), 500

    return jsonify({"ok": True, "email": buyer_email, "link": access_link})


# ======================================================
# Main
# ======================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
