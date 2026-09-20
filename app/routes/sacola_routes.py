from flask import Blueprint, request, jsonify
from services.auth import jwt_required
from ..controllers.sacola_controller import SacolaController

sacola_bp = Blueprint("sacola", __name__, url_prefix="/sacola")


@sacola_bp.route("", methods=["GET"])
@jwt_required
def ver_sacola(usuario_id):
    """Retorna o estado atual da sacola do usuário autenticado."""
    resultado, erro, status = SacolaController.consultar(usuario_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(resultado), status


@sacola_bp.route("/itens", methods=["POST"])
@jwt_required
def adicionar_item(usuario_id):
    """
    Adiciona produto na sacola.
    Payload: {"produto_id": 1, "quantidade": 2, "observacao": "Sem maionese"}
    """
    dados = request.get_json() or {}
    resultado, erro, status = SacolaController.adicionar_item(usuario_id, dados)
    if erro:
        if status == 409:
            return jsonify(resultado), status
        return jsonify({"erro": erro}), status
    return jsonify(resultado), status


@sacola_bp.route("/itens/<int:item_id>", methods=["PATCH", "PUT"])
@jwt_required
def alterar_quantidade(item_id, usuario_id):
    """
    Atualiza a quantidade de um item.
    Payload: {"quantidade": 3}
    """
    dados = request.get_json() or {}
    quantidade = dados.get("quantidade")
    if quantidade is None:
        return jsonify({"erro": "Campo 'quantidade' é obrigatório"}), 400

    resultado, erro, status = SacolaController.atualizar_quantidade(
        usuario_id, item_id, quantidade
    )
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(resultado), status


@sacola_bp.route("/itens/<int:item_id>", methods=["DELETE"])
@jwt_required
def remover_item(item_id, usuario_id):
    """Remove um item individual da sacola."""
    resultado, erro, status = SacolaController.remover_item(usuario_id, item_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(resultado), status


@sacola_bp.route("", methods=["DELETE"])
@jwt_required
def limpar_sacola(usuario_id):
    """Esvazia por completo a sacola do usuário."""
    resultado, erro, status = SacolaController.limpar_sacola(usuario_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(resultado), status