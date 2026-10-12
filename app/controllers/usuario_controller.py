from werkzeug.security import generate_password_hash
from ..database import db
from ..models.models import Usuario, Endereco
import os
import requests


class UsuarioController:

    @staticmethod
    def criar(dados):
        """Valida, cria o cliente no Asaas e persiste um novo usuário."""
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
            documento=dados.get("documento") or None
        )
        db.session.add(usuario)
        
        chave_asaas = os.getenv("CHAVE_ASAAS")
        if chave_asaas:
            url_asaas = "https://sandbox.asaas.com/api/v3/customers"
            headers = {
                "access_token": chave_asaas,
                "Content-Type": "application/json"
            }
            payload = {
                "name": usuario.nome,
                "email": usuario.email,
                "mobilePhone": usuario.telefone,
                "cpfCnpj": usuario.documento
            }
            
            try:
                resposta = requests.post(url_asaas, json=payload, headers=headers)
                if resposta.status_code == 200:
                    dados_asaas = resposta.json()
                    usuario.asaas_customer_id = dados_asaas.get("id")
                else:
                    db.session.rollback()
                    erro_msg = resposta.json().get('errors', [{'description': 'Erro no Asaas'}])[0]['description']
                    return None, f"Erro ao criar cliente na operadora: {erro_msg}", 400
            except Exception as e:
                db.session.rollback()
                return None, f"Erro de conexão com o Asaas: {str(e)}", 503

        try:
            db.session.commit()
            return usuario, None, 201
        except Exception as e:
            db.session.rollback()
            return None, f"Erro ao salvar no banco: {str(e)}", 500

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
