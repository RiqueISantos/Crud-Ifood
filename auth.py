import os
import jwt
from dotenv import load_dotenv
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta, timezone

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
TEMPO_EXPIRACAO_MINUTOS = int(os.getenv("TEMPO_EXPIRACAO_MINUTOS", 5))


def criar_token_jwt(usuario_id: int):
    payload = {
        "sub": str(usuario_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TEMPO_EXPIRACAO_MINUTOS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def token_obrigatorio(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            partes = auth_header.split()
            if len(partes) == 2 and partes[0] == 'Bearer':
                token = partes[1]

        if not token:
            return jsonify({'erro': 'Token está faltando!'}), 401

        try:
            dados_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            usuario_id = int(dados_token['sub']) 
        except jwt.ExpiredSignatureError:
            return jsonify({'erro': 'Token expirou! Faça login novamente.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'erro': 'Token inválido!'}), 401

        return f(usuario_id, *args, **kwargs)
    
    return decorated