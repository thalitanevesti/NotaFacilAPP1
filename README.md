# Nota Fácil Lite (reboot)

Gerador de recibo/nota em PDF com upload de logo e webhook do Hotmart para enviar o **link aberto** do app por e-mail.

## Rotas
- `GET /` formulário
- `POST /generate-pdf` gera e baixa PDF
- `POST /webhook/hotmart` envia e-mail com link do app quando compra estiver **aprovada**
- `GET /healthz` health check

## ENV (Render)
- `APP_NAME` (ex.: Nota Fácil Lite)
- `APP_BASE_URL` (ex.: https://seuapp.onrender.com)
- `SMTP_HOST`, `SMTP_PORT=587`, `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL`
- (opcional) `HOTMART_WEBHOOK_SECRET` para validar assinatura HMAC

## Hotmart
- **Não** anexe arquivo no Conteúdo do Produto.
- Crie **Webhook/Postback** para `/webhook/hotmart` com evento **Pagamento aprovado**.
