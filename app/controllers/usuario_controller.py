from werkzeug.security import generate_password_hash
from ..database import db
from ..models.models import Usuario


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

        if dados.get("telefone"):
            usuario.telefone = dados["telefone"]

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


    @staticmethod
    def listar_por_usuario(usuario_id):
        """Lista todos os endereços vinculados a um usuário."""
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            return None, "Usuário informado não existe", 404

        enderecos = Endereco.query.filter_by(usuario_id=usuario_id).all()
        return enderecos, None, 200

    @staticmethod
    def atualizar(id, dados):
        """
        Atualiza dados do endereço. 
        Se alterar o número, logradouro ou cidade, recalcula as coordenadas via geopy.
        """
        endereco = db.session.get(Endereco, id)
        if not endereco:
            return None, "Endereço não encontrado", 404

        if not dados:
            return None, "Dados não fornecidos", 400

        # Atualização de campos cadastrais simples
        if dados.get("tipo_endereco"):
            endereco.tipo_endereco = dados["tipo_endereco"]

        if "complemento" in dados:
            endereco.complemento = dados["complemento"]

        if dados.get("bairro"):
            endereco.bairro = dados["bairro"]

        # Se houver mudança em número, logradouro ou cidade, recalcula coordenadas
        houve_mudanca_geografica = False

        if dados.get("logradouro") and dados["logradouro"] != endereco.logradouro:
            endereco.logradouro = dados["logradouro"]
            houve_mudanca_geografica = True

        if dados.get("numero") and str(dados["numero"]) != endereco.numero:
            endereco.numero = str(dados["numero"]).strip()
            houve_mudanca_geografica = True

        if dados.get("cidade") and dados["cidade"] != endereco.cidade:
            endereco.cidade = dados["cidade"]
            houve_mudanca_geografica = True

        if dados.get("uf") and dados["uf"] != endereco.uf:
            endereco.uf = dados["uf"]
            houve_mudanca_geografica = True

        if houve_mudanca_geografica:
            lat, lng = EnderecoService.obter_coordenadas(
                endereco.logradouro, endereco.numero, endereco.cidade, endereco.uf
            )
            endereco.latitude = lat
            endereco.longitude = lng

        try:
            db.session.commit()
            return endereco, None, 200
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar endereço: {str(exc)}", 500

    @staticmethod
    def deletar(id):
        """Remove um endereço pelo ID."""
        endereco = db.session.get(Endereco, id)
        if not endereco:
            return None, "Endereço não encontrado", 404

        try:
            db.session.delete(endereco)
            db.session.commit()
            return {"mensagem": f"Endereço {id} deletado com sucesso"}, None, 200
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao deletar endereço: {str(exc)}", 500