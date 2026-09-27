from flask import Blueprint, request, jsonify
from ..controllers.usuario_controller import UsuarioController
from ..views.usuario_view import UsuarioView
from ..models.models import Usuario
from services.otp_store import enviar_otp, verificar_otp
from services.auth import criar_token_jwt

usuario_bp = Blueprint("usuario", __name__)


# ── CRUD base ────────────────────────────────────────────────────────────────

@usuario_bp.route("/", methods=["POST"])
def criar_usuario():
    dados = request.get_json() or {}
    resultado, erro, status = UsuarioController.criar(dados)
    if erro:
        return UsuarioView.resposta_mensagem({"erro": erro}, status)
    # Retorna o usuário criado + JWT para já logar direto
    token = criar_token_jwt(resultado.id)
    return jsonify({
        "access_token": token,
        "usuario": {
            "id":       resultado.id,
            "nome":     resultado.nome,
            "email":    resultado.email,
            "telefone": resultado.telefone,
        },
    }), status


@usuario_bp.route("/<int:id>", methods=["GET"])
def buscar_usuario(id):
    resultado, erro, status = UsuarioController.buscar(id)
    if erro:
        return UsuarioView.resposta_mensagem({"erro": erro}, status)
    return UsuarioView.resposta_unico(resultado, status)


@usuario_bp.route("/<int:id>", methods=["PUT"])
def atualizar_usuario(id):
    dados = request.get_json() or {}
    resultado, erro, status = UsuarioController.atualizar(id, dados)
    if erro:
        return UsuarioView.resposta_mensagem({"erro": erro}, status)
    return UsuarioView.resposta_unico(resultado, status)


@usuario_bp.route("/<int:id>", methods=["DELETE"])
def deletar_usuario(id):
    resultado, erro, status = UsuarioController.deletar(id)
    if erro:
        return UsuarioView.resposta_mensagem({"erro": erro}, status)
    return UsuarioView.resposta_mensagem(resultado, status)


# ── SMS / OTP ────────────────────────────────────────────────────────────────

@usuario_bp.route("/sms/enviar", methods=["POST"])
def sms_enviar():
    dados    = request.get_json() or {}
    telefone = (dados.get("telefone") or "").strip()

    if not telefone or len(telefone.replace(" ", "")) < 10:
        return jsonify({"erro": "Telefone inválido"}), 400

    ok, resultado = enviar_otp(telefone)
    if not ok:
        return jsonify({"erro": resultado}), 500

    return jsonify({"mensagem": "Código enviado via WhatsApp"}), 200


@usuario_bp.route("/sms/verificar", methods=["POST"])
def sms_verificar():
    dados    = request.get_json() or {}
    telefone = (dados.get("telefone") or "").strip()
    codigo   = (dados.get("codigo")   or "").strip()

    if not telefone or not codigo:
        return jsonify({"erro": "Telefone e código são obrigatórios"}), 400

    ok, msg = verificar_otp(telefone, codigo)
    if not ok:
        return jsonify({"erro": msg}), 400

    return jsonify({"mensagem": "Celular verificado com sucesso"}), 200


# ── Login por OTP ────────────────────────────────────────────────────────────

@usuario_bp.route("/login/solicitar", methods=["POST"])
def login_solicitar():
    dados         = request.get_json() or {}
    identificador = (dados.get("identificador") or "").strip()

    if not identificador:
        return jsonify({"erro": "Identificador é obrigatório"}), 400

    usuario = (
        Usuario.query.filter_by(telefone=identificador).first()
        or Usuario.query.filter_by(email=identificador).first()
    )
    if not usuario:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    if not usuario.telefone:
        return jsonify({"erro": "Usuário sem telefone cadastrado"}), 400

    ok, resultado = enviar_otp(usuario.telefone)
    if not ok:
        return jsonify({"erro": resultado}), 500

    return jsonify({"mensagem": "Código enviado via WhatsApp"}), 200


@usuario_bp.route("/login", methods=["POST"])
def login():
    dados         = request.get_json() or {}
    identificador = (dados.get("identificador") or "").strip()
    codigo        = (dados.get("codigo")        or "").strip()

    if not identificador or not codigo:
        return jsonify({"erro": "Identificador e código são obrigatórios"}), 400

    usuario = (
        Usuario.query.filter_by(telefone=identificador).first()
        or Usuario.query.filter_by(email=identificador).first()
    )
    if not usuario:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    if not usuario.telefone:
        return jsonify({"erro": "Usuário sem telefone cadastrado"}), 400

    ok, msg = verificar_otp(usuario.telefone, codigo)
    if not ok:
        return jsonify({"erro": msg}), 400

    token = criar_token_jwt(usuario.id)
    return jsonify({
        "access_token": token,
        "usuario": {
            "id":       usuario.id,
            "nome":     usuario.nome,
            "email":    usuario.email,
            "telefone": usuario.telefone,
        },
    }), 200


# ── E-mail / verificação ─────────────────────────────────────────────────────

@usuario_bp.route("/email/enviar", methods=["POST"])
def email_enviar():
    from services.email_store import enviar_codigo_email
    dados = request.get_json() or {}
    email = (dados.get("email") or "").strip().lower()

    if not email:
        return jsonify({"erro": "E-mail é obrigatório"}), 400

    ok, resultado = enviar_codigo_email(email)
    if not ok:
        return jsonify({"erro": resultado}), 500

    return jsonify({"mensagem": "Código enviado por e-mail"}), 200


@usuario_bp.route("/email/verificar", methods=["POST"])
def email_verificar():
    from services.email_store import verificar_codigo_email
    dados  = request.get_json() or {}
    email  = (dados.get("email")  or "").strip().lower()
    codigo = (dados.get("codigo") or "").strip()

    if not email or not codigo:
        return jsonify({"erro": "E-mail e código são obrigatórios"}), 400

    ok, msg = verificar_codigo_email(email, codigo)
    if not ok:
        return jsonify({"erro": msg}), 400

    return jsonify({"mensagem": "E-mail verificado com sucesso"}), 200
