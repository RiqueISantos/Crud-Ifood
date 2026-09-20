from flask import Blueprint, request, jsonify
from ..controllers.produto_controller import ProdutoController
from ..controllers.ingrediente_controller import IngredienteController
from services.auth import jwt_required

produto_bp = Blueprint("produtos", __name__, url_prefix="/produtos")

def serializar_ingrediente(ingrediente):
    return {
        "id": ingrediente.id,
        "nome": ingrediente.nome,
    }

def serializar_produto(produto):
    return {
        "id": produto.id,
        "restaurante_id": produto.restaurante_id,
        "nome": produto.nome,
        "descricao": produto.descricao,
        "preco": produto.preco,
        "disponivel": produto.disponivel,
        "criado_em": produto.criado_em.isoformat() if produto.criado_em else None,
        "ingredientes": [
            serializar_ingrediente(i) for i in (produto.ingredientes or [])
        ],
    }

@produto_bp.route("/ingredientes/autocomplete", methods=["GET"])
def autocomplete_ingredientes():
    """Retorna sugestões de ingredientes existentes para o autocomplete."""
    q = request.args.get("q", "")
    resultado, erro, status = IngredienteController.autocomplete(q)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify([serializar_ingrediente(i) for i in resultado]), status

@produto_bp.route("/restaurante/<int:restaurante_id>", methods=["GET"])
def listar_por_restaurante(restaurante_id):
    """Retorna os produtos cadastrados de um restaurante específico."""
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
        "exclude": request.args.get("exclude"),
        "restaurante_id": request.args.get("restaurante_id", type=int),
    }
    produtos, erro, status = ProdutoController.buscar(filtros)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify([serializar_produto(p) for p in produtos]), status

@produto_bp.route("/<int:id>", methods=["PUT"])
@jwt_required
def atualizar_produto(id, usuario_id):
    """Atualiza dados do produto (apenas o próprio restaurante dono pode alterar)."""
    produto, erro_busca, status_busca = ProdutoController.buscar_por_id(id)
    if erro_busca:
        return jsonify({"erro": erro_busca}), status_busca

    if produto.restaurante_id != usuario_id:
        return jsonify({"erro": "Acesso negado: este produto não pertence ao seu restaurante"}), 403

    dados = request.get_json() or {}
    resultado, erro, status = ProdutoController.atualizar(id, dados)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(serializar_produto(resultado)), status

@produto_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required
def deletar_produto(id, usuario_id):
    """Remove um produto do cardápio (apenas o restaurante dono pode remover)."""
    produto, erro_busca, status_busca = ProdutoController.buscar_por_id(id)
    if erro_busca:
        return jsonify({"erro": erro_busca}), status_busca

    if produto.restaurante_id != usuario_id:
        return jsonify({"erro": "Acesso negado: este produto não pertence ao seu restaurante"}), 403

    resultado, erro, status = ProdutoController.deletar(id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(resultado), status