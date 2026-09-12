from flask import Blueprint, request, jsonify

from ..controllers.restaurante_controller import RestauranteController
from ..views.restaurante_view import RestauranteView
from ..models.models import Restaurante
from services.auth import criar_token_jwt, jwt_required
from services.email_store import enviar_codigo_email, verificar_codigo_email

restaurante_bp = Blueprint("restaurante", __name__)


# ── Cadastro com verificação de e-mail (2 etapas) ────────────────────────────

@restaurante_bp.route("/cadastro/solicitar", methods=["POST"])
def cadastro_solicitar():
    """
    Etapa 1 do cadastro: valida se o e-mail ainda não está em uso
    e envia o código de verificação.
    """
    dados = request.get_json() or {}
    email = (dados.get("email") or "").strip().lower()

    if not email:
        return jsonify({"erro": "E-mail é obrigatório"}), 400

    if Restaurante.query.filter_by(email=email).first():
        return jsonify({"erro": "E-mail já cadastrado"}), 409

    ok, resultado = enviar_codigo_email(email)
    if not ok:
        return jsonify({"erro": resultado}), 500

    return jsonify({"mensagem": "Código de verificação enviado para o e-mail"}), 200


@restaurante_bp.route("/cadastro/confirmar", methods=["POST"])
def cadastro_confirmar():
    """
    Etapa 2 do cadastro: confirma o código de e-mail e persiste o restaurante.
    Payload completo: email, codigo, nome, telefone, categoria_principal,
                      cep, numero + opcionais (complemento, taxa_entrega, tempo_estimado).
    """
    dados = request.get_json() or {}
    email  = (dados.get("email")  or "").strip().lower()
    codigo = (dados.get("codigo") or "").strip()

    if not email or not codigo:
        return jsonify({"erro": "E-mail e código são obrigatórios"}), 400

    ok, msg = verificar_codigo_email(email, codigo)
    if not ok:
        return jsonify({"erro": msg}), 400

    # Normaliza o email no payload antes de criar
    dados["email"] = email

    resultado, erro, status = RestauranteController.criar(dados)
    if erro:
        return RestauranteView.resposta_mensagem({"erro": erro}, status)

    token = criar_token_jwt(resultado.id)
    return jsonify({
        "access_token": token,
        "restaurante": RestauranteView.serializar(resultado),
    }), status


# ── Login por e-mail (2 etapas) ───────────────────────────────────────────────

@restaurante_bp.route("/login/solicitar", methods=["POST"])
def login_solicitar():
    """
    Etapa 1 do login: localiza o restaurante pelo e-mail e envia o código.
    """
    dados = request.get_json() or {}
    email = (dados.get("email") or "").strip().lower()

    if not email:
        return jsonify({"erro": "E-mail é obrigatório"}), 400

    restaurante = Restaurante.query.filter_by(email=email).first()
    if not restaurante:
        return jsonify({"erro": "Restaurante não encontrado"}), 404

    ok, resultado = enviar_codigo_email(email)
    if not ok:
        return jsonify({"erro": resultado}), 500

    return jsonify({"mensagem": "Código de verificação enviado para o e-mail"}), 200


@restaurante_bp.route("/login", methods=["POST"])
def login():
    """
    Etapa 2 do login: valida o código e retorna o JWT.
    """
    dados  = request.get_json() or {}
    email  = (dados.get("email")  or "").strip().lower()
    codigo = (dados.get("codigo") or "").strip()

    if not email or not codigo:
        return jsonify({"erro": "E-mail e código são obrigatórios"}), 400

    restaurante = Restaurante.query.filter_by(email=email).first()
    if not restaurante:
        return jsonify({"erro": "Restaurante não encontrado"}), 404

    ok, msg = verificar_codigo_email(email, codigo)
    if not ok:
        return jsonify({"erro": msg}), 400

    token = criar_token_jwt(restaurante.id)
    return jsonify({
        "access_token": token,
        "restaurante": RestauranteView.serializar(restaurante),
    }), 200


# ── Leitura (públicas) ────────────────────────────────────────────────────────

@restaurante_bp.route("/", methods=["GET"])
def listar_restaurantes():
    """Lista todos os restaurantes. Rota pública."""
    resultado, erro, status = RestauranteController.listar()
    if erro:
        return RestauranteView.resposta_mensagem({"erro": erro}, status)
    return RestauranteView.resposta_lista(resultado, status)


@restaurante_bp.route("/<int:id>", methods=["GET"])
def buscar_restaurante(id):
    """Busca um restaurante pelo ID. Rota pública."""
    resultado, erro, status = RestauranteController.buscar(id)
    if erro:
        return RestauranteView.resposta_mensagem({"erro": erro}, status)
    return RestauranteView.resposta_unico(resultado, status)


# ── Escrita (protegidas por JWT) ──────────────────────────────────────────────

@restaurante_bp.route("/<int:id>", methods=["PUT"])
@jwt_required
def atualizar_restaurante(id, usuario_id):
    """Atualiza os dados do restaurante. Só o próprio restaurante pode alterar."""
    if usuario_id != id:
        return jsonify({"erro": "Acesso negado: você não tem permissão para alterar este restaurante"}), 403

    dados = request.get_json() or {}
    resultado, erro, status = RestauranteController.atualizar(id, dados)
    if erro:
        return RestauranteView.resposta_mensagem({"erro": erro}, status)
    return RestauranteView.resposta_unico(resultado, status)


@restaurante_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required
def deletar_restaurante(id, usuario_id):
    """Remove o restaurante. Só o próprio restaurante pode deletar."""
    if usuario_id != id:
        return jsonify({"erro": "Acesso negado: você não tem permissão para deletar este restaurante"}), 403

    resultado, erro, status = RestauranteController.deletar(id)
    if erro:
        return RestauranteView.resposta_mensagem({"erro": erro}, status)
    return RestauranteView.resposta_mensagem(resultado, status)
