from flask import Blueprint, jsonify, request
from services.auth import jwt_required
from ..controllers.produto_controller import ProdutoController

produto_bp = Blueprint("produtos", __name__)


def serializar_produto(produto):
    """Converte o modelo Produto em dicionário JSON."""
    return {
        "id": produto.id,
        "restaurante_id": produto.restaurante_id,
        "nome": produto.nome,
        "descricao": produto.descricao,
        "preco": produto.preco,
        "disponivel": produto.disponivel,
        "criado_em": produto.criado_em.isoformat() if produto.criado_em else None,
    }


@produto_bp.route("/restaurante/<int:restaurante_id>", methods=["GET"])
def listar_por_restaurante(restaurante_id):
    resultado, erro, status = ProdutoController.listar_por_restaurante(restaurante_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify([serializar_produto(p) for p in resultado]), status


@produto_bp.route("/", methods=["POST"])
@jwt_required
def criar_produto(usuario_id):
    dados = request.get_json() or {}
    dados["restaurante_id"] = usuario_id
    produto, erro, status = ProdutoController.criar(dados)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(serializar_produto(produto)), status


@produto_bp.route("/busca", methods=["GET"])
def buscar_produtos():
    filtros = {
        "q": request.args.get("q"),
        "restaurante_id": request.args.get("restaurante_id", type=int),
    }
    produtos, erro, status = ProdutoController.buscar(filtros)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify([serializar_produto(p) for p in produtos]), status


@produto_bp.route("/<int:id>", methods=["PUT"])
@jwt_required
def atualizar_produto(id, usuario_id):
    produto, erro_busca, status_busca = ProdutoController.buscar_por_id(id)
    if erro_busca:
        return jsonify({"erro": erro_busca}), status_busca
    if produto.restaurante_id != usuario_id:
        return jsonify({"erro": "Acesso negado"}), 403
    dados = request.get_json() or {}
    resultado, erro, status = ProdutoController.atualizar(id, dados)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(serializar_produto(resultado)), status


@produto_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required
def deletar_produto(id, usuario_id):
    produto, erro_busca, status_busca = ProdutoController.buscar_por_id(id)
    if erro_busca:
        return jsonify({"erro": erro_busca}), status_busca
    if produto.restaurante_id != usuario_id:
        return jsonify({"erro": "Acesso negado"}), 403
    resultado, erro, status = ProdutoController.deletar(id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(resultado), status
