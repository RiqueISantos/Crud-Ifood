from flask import jsonify

class RestauranteView:

    @staticmethod
    def serializar(restaurante):
        """Serializa um único objeto Restaurante para dict."""
        return {
            "id": restaurante.id,
            "nome": restaurante.nome,
            "email": restaurante.email,
            "telefone": restaurante.telefone,
            "categoria_principal": restaurante.categoria_principal,
            "taxa_entrega": float(restaurante.taxa_entrega) if restaurante.taxa_entrega else None,
            "tempo_estimado": restaurante.tempo_estimado,
            # Dados de endereço que ficam na própria tabela do restaurante
            "cep": restaurante.cep,
            "logradouro": restaurante.logradouro,
            "numero": restaurante.numero,
            "complemento": restaurante.complemento,
            "bairro": restaurante.bairro,
            "cidade": restaurante.cidade,
            "uf": restaurante.uf,
            "latitude": float(restaurante.latitude) if restaurante.latitude else None,
            "longitude": float(restaurante.longitude) if restaurante.longitude else None,
            "criado_em": restaurante.criado_em.isoformat() if restaurante.criado_em else None,
        }

    @staticmethod
    def resposta_unico(restaurante, status):
        return jsonify(RestauranteView.serializar(restaurante)), status

    @staticmethod
    def resposta_lista(restaurantes, status):
        return jsonify([RestauranteView.serializar(r) for r in restaurantes]), status

    @staticmethod
    def resposta_mensagem(dados, status):
        return jsonify(dados), status