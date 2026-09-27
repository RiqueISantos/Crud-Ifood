from app.database import db
from ..models.models import Sacola, ItemSacola, Produto, Restaurante


class SacolaController:

    @staticmethod
    def consultar(usuario_id):
        """Retorna a sacola atual do usuário com os cálculos de subtotal e total."""
        sacola = db.session.query(Sacola).filter_by(usuario_id=usuario_id).first()
        if not sacola or not sacola.itens:
            return {
                "id": sacola.id if sacola else None,
                "restaurante": None,
                "itens": [],
                "subtotal": 0.0,
                "taxa_entrega": 0.0,
                "total": 0.0,
            }, None, 200

        restaurante = db.session.get(Restaurante, sacola.restaurante_id)
        subtotal = sum(item.produto.preco * item.quantidade for item in sacola.itens)
        taxa_entrega = restaurante.taxa_entrega if restaurante and restaurante.taxa_entrega else 0.0

        dados = {
            "id": sacola.id,
            "restaurante": {
                "id": restaurante.id,
                "nome": restaurante.nome,
                "taxa_entrega": taxa_entrega,
                "tempo_estimado": restaurante.tempo_estimado,
            },
            "itens": [
                {
                    "id": item.id,
                    "produto_id": item.produto.id,
                    "nome": item.produto.nome,
                    "preco_unitario": item.produto.preco,
                    "quantidade": item.quantidade,
                    "observacao": item.observacao,
                    "subtotal_item": round(item.produto.preco * item.quantidade, 2),
                }
                for item in sacola.itens
            ],
            "subtotal": round(subtotal, 2),
            "taxa_entrega": round(taxa_entrega, 2),
            "total": round(subtotal + taxa_entrega, 2),
        }
        return dados, None, 200

    @staticmethod
    def adicionar_item(usuario_id, dados):
        """
        Adiciona item à sacola.
        dados esperados:
          - produto_id (int, obrigatório)
          - quantidade (int, opcional, default 1)
          - observacao (str, opcional)
          - substituir_sacola (bool, opcional, default False)
        """
        produto_id = dados.get("produto_id")
        quantidade = dados.get("quantidade", 1)
        observacao = dados.get("observacao")
        substituir_sacola = dados.get("substituir_sacola", False)

        if not produto_id:
            return None, "produto_id é obrigatório", 400
        if quantidade <= 0:
            return None, "A quantidade deve ser maior que zero", 400

        produto = db.session.get(Produto, produto_id)
        if not produto:
            return None, "Produto não encontrado", 404
        if not produto.disponivel:
            return None, "Este produto não está disponível no momento", 400

        sacola = db.session.query(Sacola).filter_by(usuario_id=usuario_id).first()

        if sacola:
            if sacola.restaurante_id != produto.restaurante_id:
                if not substituir_sacola:
                    restaurante_atual = db.session.get(Restaurante, sacola.restaurante_id)
                    return {
                        "conflito": True,
                        "mensagem": f"Sua sacola já contém itens de '{restaurante_atual.nome}'. Deseja limpar a sacola e iniciar uma nova?",
                    }, "Conflito de restaurante", 409

                db.session.query(ItemSacola).filter_by(sacola_id=sacola.id).delete()
                sacola.restaurante_id = produto.restaurante_id
        else:
            sacola = Sacola(usuario_id=usuario_id, restaurante_id=produto.restaurante_id)
            db.session.add(sacola)
            db.session.flush()

        item_existente = (
            db.session.query(ItemSacola)
            .filter_by(
                sacola_id=sacola.id,
                produto_id=produto.id,
                observacao=observacao,
            )
            .first()
        )

        if item_existente:
            item_existente.quantidade += quantidade
        else:
            novo_item = ItemSacola(
                sacola_id=sacola.id,
                produto_id=produto.id,
                quantidade=quantidade,
                observacao=observacao,
            )
            db.session.add(novo_item)

        db.session.commit()
        return SacolaController.consultar(usuario_id)

    @staticmethod
    def atualizar_quantidade(usuario_id, item_id, nova_quantidade):
        """Atualiza a quantidade de um item. Se a quantidade for <= 0, remove o item."""
        sacola = db.session.query(Sacola).filter_by(usuario_id=usuario_id).first()
        if not sacola:
            return None, "Sacola não encontrada", 404

        item = (
            db.session.query(ItemSacola)
            .filter_by(id=item_id, sacola_id=sacola.id)
            .first()
        )
        if not item:
            return None, "Item não encontrado na sua sacola", 404

        if nova_quantidade <= 0:
            db.session.delete(item)
        else:
            item.quantidade = nova_quantidade

        db.session.commit()

        if not sacola.itens:
            db.session.delete(sacola)
            db.session.commit()
            return {"mensagem": "Sacola esvaziada"}, None, 200

        return SacolaController.consultar(usuario_id)

    @staticmethod
    def remover_item(usuario_id, item_id):
        """Remove diretamente um item da sacola."""
        return SacolaController.atualizar_quantidade(usuario_id, item_id, 0)

    @staticmethod
    def limpar_sacola(usuario_id):
        """Remove a sacola inteira e todos os itens do usuário."""
        sacola = db.session.query(Sacola).filter_by(usuario_id=usuario_id).first()
        if sacola:
            db.session.delete(sacola)
            db.session.commit()
        return {"mensagem": "Sacola limpa com sucesso"}, None, 200