# Nota Fácil Lite — App de Recibo/Nota em PDF (MVP)

**Aviso**: Este app gera um *recibo/nota simples* em PDF com seu logo e dados. **Não substitui NF-e/NFS-e oficial.**  
Ideal para autônomos e pequenos negócios que desejam um documento bonito para o cliente.

## 🔧 Stack
- Python + Flask
- Geração de PDF com ReportLab
- Upload de logo (PNG/JPG)
- Proteção de acesso por **token JWT** (query string `?t=...`)
- Rate limit básico com Flask-Limiter

## ▶️ Rodando localmente
Requisitos: Python 3.11+

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # no Windows: copy .env.example .env
python app.py
```

Acesse: http://127.0.0.1:5000/?t=LOCAL-DEV  (como DISABLE_AUTH=true no .env.example, qualquer token serve).

## 🔐 Gerando token JWT (para produção)
Para restringir acesso em produção, gere tokens específicos por e-mail com vencimento:

```bash
python scripts/make_token.py --email cliente@exemplo.com --days 365
```

Saída: um token que você inclui no link de acesso, por exemplo:  
`https://SEU-APP.onrender.com/?t=TOKENAQUI`

> No Render, configure a env var **JWT_SECRET**. Em dev local, está em `.env`.

## ☁️ Deploy no Render (grátis)
1. Crie repositório no GitHub com estes arquivos.
2. No [Render](https://render.com), **New +** → **Web Service** → importe o repo.
3. Runtime: **Python**. Ele lerá `render.yaml` e instalará tudo.
4. Defina `JWT_SECRET` (automaticamente criado pelo `render.yaml`) e mantenha `DISABLE_AUTH=false` em produção.
5. Deploy. Link ficará algo como `https://nota-facil-lite.onrender.com/`.

## 🧪 Endpoints
- `GET /` — formulário (valida token quando `DISABLE_AUTH=false`).
- `POST /generate` — gera e retorna o PDF.
- `GET /health` — healthcheck.

## 📄 Campos do formulário
- **Dados da empresa:** nome, CNPJ/CPF, endereço, e **logo** (PNG/JPG até 2MB).
- **Dados do cliente:** nome, CPF/CNPJ.
- **Documento:** número, data, descrição, valor.

## 🛡️ Dificultando compartilhamento
- Links com **token individual** por e-mail (JWT com `email` + `exp`).
- Revogue mudando o `JWT_SECRET` (invalida todos) ou reduzindo validade dos tokens.
- Para vendas pela Hotmart, entregue o link na **Área de Membros** com token por comprador (integração posterior).

## 📌 Limitações
- Sem banco de dados (MVP). Nada é salvo no servidor.
- Não emite NF-e oficial.
