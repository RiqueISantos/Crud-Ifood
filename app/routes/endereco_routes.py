from flask import Blueprint, request, jsonify
from ..controllers.endereco_controller import EnderecoController

endereco_bp = Blueprint("enderecos", __name__)


def formatar_endereco(e):
    """Helper para padronizar a serialização de Endereço em JSON."""
    return {
        "id": e.id,
        "usuario_id": e.usuario_id,
        "tipo_endereco": e.tipo_endereco,
        "cep": e.cep,
        "logradouro": e.logradouro,
        "numero": e.numero,
        "complemento": e.complemento,
        "bairro": e.bairro,
        "cidade": e.cidade,
        "uf": e.uf,
        "latitude": e.latitude,
        "longitude": e.longitude
    }

@endereco_bp.route("/consulta-cep/<cep>", methods=["GET"])
def rota_consultar_cep(cep):
    dados, erro, status = EnderecoController.consultar_cep(cep)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(dados), status

@endereco_bp.route("", methods=["POST"])
@endereco_bp.route("/", methods=["POST"])
def rota_salvar_endereco():
    dados = request.get_json() or {}
    endereco, erro, status = EnderecoController.salvar(dados)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(formatar_endereco(endereco)), status


# Buscar por ID
@endereco_bp.route("/<int:id>", methods=["GET"])
def rota_buscar_endereco(id):
    endereco, erro, status = EnderecoController.buscar_por_id(id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(formatar_endereco(endereco)), status


# Listar endereços do usuário
@endereco_bp.route("/usuario/<int:usuario_id>", methods=["GET"])
def rota_listar_enderecos_usuario(usuario_id):
    enderecos, erro, status = EnderecoController.listar_por_usuario(usuario_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify([formatar_endereco(e) for e in enderecos]), status


# Atualizar endereço
@endereco_bp.route("/<int:id>", methods=["PUT"])
def rota_atualizar_endereco(id):
    dados = request.get_json() or {}
    endereco, erro, status = EnderecoController.atualizar(id, dados)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(formatar_endereco(endereco)), status


# Deletar endereço
@endereco_bp.route("/<int:id>", methods=["DELETE"])
def rota_deletar_endereco(id):
    resultado, erro, status = EnderecoController.deletar(id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(resultado), status