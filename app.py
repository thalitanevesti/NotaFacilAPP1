import os
from datetime import datetime
from io import BytesIO

from flask import Flask, render_template, request, send_file, abort, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from utils.pdf import build_pdf
import jwt
import smtplib, ssl
from email.message import EmailMessage
from datetime import timedelta

load_dotenv()
app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB para upload do logo
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() == "true"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")

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


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
@limiter.limit("60/minute")
def index():
    payload = _verify_token()
    if payload is None:
        abort(401, description="Acesso não autorizado. Token ausente ou inválido.")
    return render_template("index.html", payload=payload)

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


    # --- Hotmart Webhook Integration ---
    from flask import jsonify
    import smtplib, ssl
    from email.message import EmailMessage
    from datetime import timedelta

def send_access_email(to_email: str, access_link: str) -> None:
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "no-reply@seuapp.com")

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


    @app.post("/hotmart/webhook")
    def hotmart_webhook():
        expected = os.getenv("HOTMART_SECRET")
        got = request.headers.get("X-Hotmart-Secret")
        if expected and expected != got:
            return jsonify({"ok": False, "error": "invalid signature"}), 401

        data = request.json or request.form.to_dict()
        buyer_email = (data.get("buyer_email") or data.get("email") or "").strip().lower()
        status = (data.get("status") or data.get("purchase_status") or "").upper()

        if not buyer_email:
            return jsonify({"ok": False, "error": "missing email"}), 400

        if status not in {"APPROVED", "PAID"}:
            return jsonify({"ok": True, "ignored": status}), 200

        exp = datetime.utcnow() + timedelta(days=365)
        token = jwt.encode({"email": buyer_email, "exp": exp}, JWT_SECRET, algorithm="HS256")

        app_url = os.getenv("APP_URL", "https://nota-facil-lite.onrender.com")
        access_link = f"{app_url}/?t={token}"

        try:
            send_access_email(buyer_email, access_link)
        except Exception as e:
            return jsonify({"ok": False, "error": f"email fail: {e}"}), 500

        return jsonify({"ok": True, "email": buyer_email, "link": access_link})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
