"""
auth.py — Utilitários de autenticação JWT

Usado pelo oauth_routes e pelo fluxo de login OTP.
"""
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "ifood_secret_jwt_2026")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")
EXPIRY_MIN = int(os.getenv("TEMPO_EXPIRACAO_MINUTOS", "60"))


def criar_token_jwt(usuario_id: int) -> str:
    """Gera um token JWT assinado com o id do usuário."""
    payload = {
        "sub": str(usuario_id),
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=EXPIRY_MIN),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token_jwt(token: str) -> dict:
    """
    Decodifica e valida o token JWT.
    Lança jwt.ExpiredSignatureError ou jwt.InvalidTokenError em caso de falha.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
