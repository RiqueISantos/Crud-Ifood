from werkzeug.security import generate_password_hash
from ..database import db
from ..models.models import Usuario, Endereco


class UsuarioController:

    @staticmethod
    def criar(dados):
        """Valida e persiste um novo usuário."""
        campos_obrigatorios = ["nome", "email"]
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return None, f"Campo '{campo}' é obrigatório", 400

        if Usuario.query.filter_by(email=dados["email"]).first():
            return None, "E-mail já cadastrado", 409

        usuario = Usuario(
            nome=dados["nome"],
            email=dados["email"],
            telefone=dados.get("telefone") or None,
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario, None, 201

    @staticmethod
    def buscar(id):
        """Busca um usuário pelo id."""
        usuario = db.session.get(Usuario, id)
        if not usuario:
            return None, "Usuário não encontrado", 404
        return usuario, None, 200

    @staticmethod
    def atualizar(usuario_id, dados):
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            return None, "Utilizador não encontrado", 404

        if "nome" in dados:
            usuario.nome = dados["nome"]
        if "telefone" in dados:
            usuario.telefone = dados["telefone"]
        if "documento" in dados:
            usuario.documento = dados["documento"]

        try:
            db.session.commit()
            return usuario, None, 200
        except Exception as e:
            db.session.rollback()
            return None, f"Erro ao atualizar utilizador: {str(e)}", 500

    @staticmethod
    def deletar(id):
        """Remove um usuário pelo id."""
        usuario = db.session.get(Usuario, id)
        if not usuario:
            return None, "Usuário não encontrado", 404

        db.session.delete(usuario)
        db.session.commit()
        return {"mensagem": f"Usuário {id} deletado com sucesso"}, None, 200
