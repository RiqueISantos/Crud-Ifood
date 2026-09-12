"""
auth.py — Utilitários de autenticação JWT

Usado pelo oauth_routes e pelo fluxo de login OTP.
"""
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import request, jsonify
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


def jwt_required(f):
    """
    Decorator que protege uma rota exigindo um JWT válido no header:
        Authorization: Bearer <token>

    Em caso de sucesso, injeta `usuario_id` (int) como kwarg na função decorada.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"erro": "Token de autenticação não fornecido"}), 401

        token = auth_header.split(" ", 1)[1].strip()

        try:
            payload = verificar_token_jwt(token)
            usuario_id = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            return jsonify({"erro": "Token expirado. Faça login novamente"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"erro": "Token inválido"}), 401

        return f(*args, usuario_id=usuario_id, **kwargs)

    return decorated
