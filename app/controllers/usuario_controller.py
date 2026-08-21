from werkzeug.security import generate_password_hash
from ..database import db
from ..models.usuario import Usuario


class UsuarioController:

    @staticmethod
    def criar(dados):
        """Valida e persiste um novo usuário."""
        campos_obrigatorios = ["nome", "email", "senha"]
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return None, f"Campo '{campo}' é obrigatório", 400

        if Usuario.query.filter_by(email=dados["email"]).first():
            return None, "E-mail já cadastrado", 409

        usuario = Usuario(
            nome=dados["nome"],
            email=dados["email"],
            senha=generate_password_hash(dados["senha"]),
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario, None, 201

    @staticmethod
    def listar():
        """Retorna todos os usuários ordenados por id."""
        usuarios = Usuario.query.order_by(Usuario.id).all()
        return usuarios, None, 200

    @staticmethod
    def buscar(id):
        """Busca um usuário pelo id."""
        usuario = db.session.get(Usuario, id)
        if not usuario:
            return None, "Usuário não encontrado", 404
        return usuario, None, 200

    @staticmethod
    def atualizar(id, dados):
        """Atualiza os dados de um usuário existente."""
        usuario = db.session.get(Usuario, id)
        if not usuario:
            return None, "Usuário não encontrado", 404

        if not dados:
            return None, "Dados não fornecidos", 400

        if dados.get("nome"):
            usuario.nome = dados["nome"]

        if dados.get("email"):
            existente = Usuario.query.filter_by(email=dados["email"]).first()
            if existente and existente.id != id:
                return None, "E-mail já cadastrado por outro usuário", 409
            usuario.email = dados["email"]

        if dados.get("senha"):
            usuario.senha = generate_password_hash(dados["senha"])

        db.session.commit()
        return usuario, None, 200

    @staticmethod
    def deletar(id):
        """Remove um usuário pelo id."""
        usuario = db.session.get(Usuario, id)
        if not usuario:
            return None, "Usuário não encontrado", 404

        db.session.delete(usuario)
        db.session.commit()
        return {"mensagem": f"Usuário {id} deletado com sucesso"}, None, 200
