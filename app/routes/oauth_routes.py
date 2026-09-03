import os
import json
import time
import hmac
import hashlib
from urllib.parse import quote

from flask import Blueprint, redirect, request, jsonify
from authlib.integrations.requests_client import OAuth2Session
from dotenv import load_dotenv

from app.database import db
from app.models.usuario import Usuario
from app.services.otp_store import enviar_otp, verificar_otp
from auth import criar_token_jwt

load_dotenv()

oauth_bp = Blueprint("oauth", __name__)

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/google/callback")
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:5174")
SECRET_KEY           = os.getenv("SECRET_KEY", "ifood_secret_jwt_2026")

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES           = "openid email profile"

OAUTH_TEMP_TTL = 600  # segundos de validade do token temporário


# ── Token temporário (HMAC — sem dep extra) ──────────────────────────────────

def _gerar_temp_token(usuario_id: int) -> str:
    ts      = int(time.time())
    payload = f"{usuario_id}.{ts}"
    sig     = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _validar_temp_token(token: str):
    """Retorna usuario_id (int) ou None se inválido/expirado."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        uid_str, ts_str, sig = parts
        payload  = f"{uid_str}.{ts_str}"
        expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        if int(time.time()) - int(ts_str) > OAUTH_TEMP_TTL:
            return None
        return int(uid_str)
    except Exception:
        return None


# ── Rotas ────────────────────────────────────────────────────────────────────

@oauth_bp.route("/auth/google")
def google_login():
    """Redireciona para a tela de login do Google."""
    client = OAuth2Session(
        client_id=GOOGLE_CLIENT_ID,
        redirect_uri=GOOGLE_REDIRECT_URI,
        scope=SCOPES,
    )
    uri, _ = client.create_authorization_url(GOOGLE_AUTH_URL)
    return redirect(uri)


@oauth_bp.route("/auth/google/callback")
def google_callback():
    """
    Recebe o code do Google, busca/cria o usuário e redireciona para o
    frontend com um token TEMPORÁRIO.
    O JWT definitivo só é emitido após confirmação do celular.
    """
    code = request.args.get("code")
    if not code:
        return redirect(f"{FRONTEND_URL}/#/auth?erro=oauth_cancelado")

    try:
        client = OAuth2Session(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            redirect_uri=GOOGLE_REDIRECT_URI,
        )
        client.fetch_token(GOOGLE_TOKEN_URL, code=code)
        resp = client.get(GOOGLE_USERINFO)
        info = resp.json()

        email = info.get("email", "").lower().strip()
        nome  = info.get("name", email.split("@")[0])

        if not email:
            return redirect(f"{FRONTEND_URL}/#/auth?erro=email_nao_encontrado")

        # Busca ou cria o usuário (sem telefone por enquanto)
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            usuario = Usuario(nome=nome, email=email)
            db.session.add(usuario)
            db.session.commit()

        temp_token   = _gerar_temp_token(usuario.id)
        tem_telefone = bool(usuario.telefone)
        usuario_str  = quote(json.dumps({
            "id":       usuario.id,
            "nome":     usuario.nome,
            "email":    usuario.email,
            "telefone": usuario.telefone or "",
        }))

        return redirect(
            f"{FRONTEND_URL}/#/oauth-callback"
            f"?temp_token={temp_token}"
            f"&tem_telefone={'1' if tem_telefone else '0'}"
            f"&usuario={usuario_str}"
        )

    except Exception as e:
        print(f"[OAuth Google] Erro: {e}")
        return redirect(f"{FRONTEND_URL}/#/auth?erro=oauth_falhou")


@oauth_bp.route("/auth/google/enviar-sms", methods=["POST"])
def google_enviar_sms():
    """
    Envia OTP para o telefone informado durante o fluxo OAuth.
    Body: { temp_token, telefone }
    """
    dados      = request.get_json() or {}
    temp_token = dados.get("temp_token", "")
    telefone   = (dados.get("telefone") or "").strip()

    if not _validar_temp_token(temp_token):
        return jsonify({"erro": "Sessão expirada. Faça login com o Google novamente."}), 401

    if not telefone or len(telefone.replace(" ", "")) < 10:
        return jsonify({"erro": "Telefone inválido"}), 400

    ok, resultado = enviar_otp(telefone)
    if not ok:
        return jsonify({"erro": resultado}), 500

    return jsonify({"mensagem": "Código enviado via WhatsApp"}), 200


@oauth_bp.route("/auth/google/confirmar", methods=["POST"])
def google_confirmar():
    """
    Valida OTP e retorna o JWT definitivo.
    Body: { temp_token, telefone, codigo }
    """
    dados      = request.get_json() or {}
    temp_token = dados.get("temp_token", "")
    telefone   = (dados.get("telefone") or "").strip()
    codigo     = (dados.get("codigo")   or "").strip()

    # 1. Valida token temporário
    usuario_id = _validar_temp_token(temp_token)
    if not usuario_id:
        return jsonify({"erro": "Sessão expirada. Faça login com o Google novamente."}), 401

    # 2. Verifica OTP
    ok, msg = verificar_otp(telefone, codigo)
    if not ok:
        return jsonify({"erro": msg}), 400

    # 3. Atualiza telefone se ainda não tinha
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return jsonify({"erro": "Usuário não encontrado."}), 404

    if telefone and not usuario.telefone:
        usuario.telefone = telefone
        db.session.commit()

    # 4. Retorna JWT definitivo
    jwt_token = criar_token_jwt(usuario.id)
    return jsonify({
        "access_token": jwt_token,
        "usuario": {
            "id":       usuario.id,
            "nome":     usuario.nome,
            "email":    usuario.email,
            "telefone": usuario.telefone,
        },
    }), 200
