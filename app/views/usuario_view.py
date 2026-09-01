from flask import jsonify


class UsuarioView:

    @staticmethod
    def serializar(usuario):
        """Serializa um único objeto Usuario para dict."""
        return {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "criado_em": usuario.criado_em.isoformat() if usuario.criado_em else None,
        }

    @staticmethod
    def resposta_unico(usuario, status):
        """Retorna resposta JSON de um único usuário."""
        return jsonify(UsuarioView.serializar(usuario)), status

    @staticmethod
    def resposta_lista(usuarios, status):
        """Retorna resposta JSON de uma lista de usuários."""
        return jsonify([UsuarioView.serializar(u) for u in usuarios]), status

    @staticmethod
    def resposta_mensagem(dados, status):
        """Retorna resposta JSON de uma mensagem simples ou erro."""
        return jsonify(dados), status
