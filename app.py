import os, hmac, hashlib, base64, ssl
from flask import Flask, render_template, request, send_file, jsonify
import smtplib
from email.message import EmailMessage
from utils.pdf import gerar_pdf

# ===== Config por ENV =====
APP_NAME = os.getenv("APP_NAME", "Nota Fácil Lite")
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://SEUAPP.onrender.com").rstrip("/")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", "no-reply@seuapp.com")

# (Opcional) Validação HMAC do Hotmart; se não quiser validar, não defina.
HOTMART_WEBHOOK_SECRET = os.getenv("HOTMART_WEBHOOK_SECRET")

def _send_access_email(to_email: str, app_link: str) -> None:
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS]):
        raise RuntimeError("SMTP não configurado")
    msg = EmailMessage()
    msg["Subject"] = f"Seu acesso ao {APP_NAME}"
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    body = (
        f"Olá!\n\n"
        f"Obrigada pela compra. Acesse seu produto aqui:\n{app_link}\n\n"
        f"Qualquer dúvida, responda este e-mail.\n"
        f"Bom uso! 💛"
    )
    msg.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

def _verify_hotmart_signature(raw_body: bytes, header_sig: str) -> bool:
    """Se HOTMART_WEBHOOK_SECRET existir, valida HMAC; senão, libera."""
    if not HOTMART_WEBHOOK_SECRET:
        return True
    if not header_sig:
        return False
    digest = hmac.new(HOTMART_WEBHOOK_SECRET.encode(), msg=raw_body, digestmod=hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(header_sig, expected)

def _status_is_approved(status) -> bool:
    s = str(status or "").lower()
    return s in {"approved", "approved_with_boleto", "completed", "pago", "aprovado"}

def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html", app_name=APP_NAME)

    @app.post("/generate-pdf")
    def generate_pdf_route():
        # Aceita form-data (com arquivo) ou JSON
        dados = request.get_json(silent=True)
        if not dados:
            f = request.form.to_dict(flat=True)
            dados = {
                "company_name": f.get("company_name", ""),
                "company_doc": f.get("company_doc", ""),
                "company_address": f.get("company_address", ""),
                "client_name": f.get("client_name", ""),
                "client_doc": f.get("client_doc", ""),
                "doc_number": f.get("doc_number", ""),
                "issue_date": f.get("issue_date", ""),
                "description": f.get("description", ""),
                "value": f.get("value", ""),
            }
        logo_file = request.files.get("logo")
        logo_bytes = logo_file.read() if logo_file and logo_file.filename else None

        pdf_io = gerar_pdf(dados, logo_bytes=logo_bytes)
        return send_file(pdf_io, mimetype="application/pdf",
                         as_attachment=True, download_name="recibo.pdf")

    @app.post("/webhook/hotmart")
    def webhook_hotmart():
        # Validação opcional
        if not _verify_hotmart_signature(request.data, request.headers.get("X-Hotmart-Hmac-SHA256")):
            return jsonify(ok=False, error="assinatura inválida"), 401

        data = request.get_json(silent=True) or {}
        buyer_email = (
            data.get("buyer", {}).get("email")
            or data.get("data", {}).get("buyer", {}).get("email")
            or data.get("purchase", {}).get("buyer", {}).get("email")
        )
        status = (
            data.get("status")
            or data.get("purchase", {}).get("status")
            or data.get("data", {}).get("status")
        )
        if not buyer_email:
            return jsonify(ok=False, error="email não encontrado"), 400
        if not _status_is_approved(status):
            return jsonify(ok=True, ignored=True, status=status), 200

        try:
            _send_access_email(buyer_email, APP_BASE_URL or "https://google.com")
        except Exception as e:
            print("Erro SMTP:", repr(e))
            return jsonify(ok=False, error="falha no envio e-mail"), 500

        print({"buyer": buyer_email, "sent_link": APP_BASE_URL})
        return jsonify(ok=True, link=APP_BASE_URL), 200

    @app.get("/healthz")
    def healthz():
        return jsonify(ok=True)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
