from flask import Blueprint, request
from ..controllers.usuario_controller import UsuarioController
from ..views.usuario_view import UsuarioView

usuario_bp = Blueprint("usuario", __name__)


@usuario_bp.route("/", methods=["POST"])
def criar_usuario():
    dados = request.get_json() or {}
    resultado, erro, status = UsuarioController.criar(dados)
    if erro:
        return UsuarioView.resposta_mensagem({"erro": erro}, status)
    return UsuarioView.resposta_unico(resultado, status)


@usuario_bp.route("/", methods=["GET"])
def listar_usuarios():
    resultado, erro, status = UsuarioController.listar()
    if erro:
        return UsuarioView.resposta_mensagem({"erro": erro}, status)
    return UsuarioView.resposta_lista(resultado, status)


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
