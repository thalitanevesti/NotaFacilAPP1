import os, argparse, time, jwt, secrets
from datetime import datetime, timedelta

def main():
    parser = argparse.ArgumentParser(description="Gerador de token JWT para acesso ao app")
    parser.add_argument("--email", required=True, help="E-mail do comprador/usuário")
    parser.add_argument("--days", type=int, default=365, help="Validade em dias (padrão: 365)")
    parser.add_argument("--secret", default=None, help="JWT secret (padrão: env JWT_SECRET ou 'dev-secret')")
    args = parser.parse_args()

    secret = args.secret or os.getenv("JWT_SECRET", "dev-secret")
    exp = datetime.utcnow() + timedelta(days=args.days)
    payload = {"email": args.email, "exp": exp}
    token = jwt.encode(payload, secret, algorithm="HS256")
    print(token)

if __name__ == "__main__":
    main()
