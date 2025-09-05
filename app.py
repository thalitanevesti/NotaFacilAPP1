@app.post("/webhook/hotmart")
def hotmart_webhook():
    # 1) Valida segredo se vier no header (opcional)
    expected = os.getenv("WEBHOOK_SECRET")
    got = request.headers.get("x-hotmart-secret")
    if expected and got and expected != got:
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

    # 4) Gera token JWT
    exp = datetime.utcnow() + timedelta(days=365)
    token = jwt.encode({"email": buyer_email, "exp": exp}, JWT_SECRET, algorithm="HS256")

    app_url = os.getenv("APP_URL", "https://notafacilapp1.onrender.com")
    access_link = f"{app_url}/?t={token}"

    # 5) Envia e-mail em background (pra não dar timeout 408)
    from threading import Thread
    def _bg_send():
        try:
            import socket
            socket.setdefaulttimeout(10)
            send_access_email(buyer_email, access_link)
        except Exception as e:
            print(f"[SMTP] erro ao enviar para {buyer_email}: {e}")

    Thread(target=_bg_send, daemon=True).start()

    # 6) Responde rápido pra Hotmart não dar 408
    return jsonify({"ok": True, "email": buyer_email, "link": access_link}), 200
