# ======== Hotmart Webhook ========

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
    """
    event = payload.get("event") or ""
    data = payload.get("data") or {}

    buyer = data.get("buyer") or {}
    email = (buyer.get("email") or "").strip().lower()

    purchase = data.get("purchase") or {}
    status = (purchase.get("status") or "").upper()
    transaction = purchase.get("transaction") or purchase.get("transaction_id") or ""

    # Fallback para testes simples
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

    # 4) Gera token JWT (igual no resto do app)
    exp = datetime.utcnow() + timedelta(days=365)
    token = jwt.encode({"email": buyer_email, "exp": exp}, JWT_SECRET, algorithm="HS256")

    app_url = os.getenv("APP_URL", "https://nota-facil-lite.onrender.com")
    access_link = f"{app_url}/?t={token}"

    # 5) Envia e-mail
    try:
        send_access_email(buyer_email, access_link)
    except Exception as e:
        return jsonify({"ok": False, "error": f"email fail: {e}"}), 500

    return jsonify({"ok": True, "email": buyer_email, "link": access_link})


# ======== /Hotmart Webhook ========

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
