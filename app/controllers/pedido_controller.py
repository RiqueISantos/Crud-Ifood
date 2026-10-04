from ..database import db
from ..models.models import (
    Pedido, ItemPedido, Sacola, Endereco,
    StatusPedido, FormaPagamento
)


# Transições de status permitidas — só o restaurante avança o pedido
_TRANSICOES_RESTAURANTE = {
    StatusPedido.AGUARDANDO_CONFIRMACAO: StatusPedido.CONFIRMADO,
    StatusPedido.CONFIRMADO:             StatusPedido.EM_PREPARACAO,
    StatusPedido.EM_PREPARACAO:          StatusPedido.SAIU_PARA_ENTREGA,
    StatusPedido.SAIU_PARA_ENTREGA:      StatusPedido.ENTREGUE,
}


class PedidoController:

    # ------------------------------------------------------------------
    # Confirmar pedido (usuário converte a sacola em pedido)
    # ------------------------------------------------------------------

    @staticmethod
    def confirmar(usuario_id: int, dados: dict):
        """
        Converte a sacola atual do usuário em um Pedido.
        dados esperados:
          - endereco_id      (int, obrigatório)
          - forma_pagamento  (str, obrigatório) — CREDITO, DEBITO, PIX, DINHEIRO, VALE
          - observacao       (str, opcional)
        """
        endereco_id     = dados.get("endereco_id")
        forma_pgto_str  = (dados.get("forma_pagamento") or "").strip().upper()
        observacao      = dados.get("observacao")

        if not endereco_id:
            return None, "Campo 'endereco_id' é obrigatório", 400

        if not forma_pgto_str:
            return None, "Campo 'forma_pagamento' é obrigatório", 400

        try:
            forma_pagamento = FormaPagamento[forma_pgto_str]
        except KeyError:
            opcoes = ", ".join([f.value for f in FormaPagamento])
            return None, f"Forma de pagamento inválida. Opções: {opcoes}", 400

        # Valida endereço e ownership
        endereco = db.session.get(Endereco, endereco_id)
        if not endereco:
            return None, "Endereço não encontrado", 404
        if endereco.usuario_id != usuario_id:
            return None, "Acesso negado: endereço não pertence ao usuário", 403

        # Busca sacola com itens
        sacola = db.session.query(Sacola).filter_by(usuario_id=usuario_id).first()
        if not sacola or not sacola.itens:
            return None, "Sacola vazia. Adicione produtos antes de confirmar o pedido", 400

        restaurante = sacola.restaurante
        subtotal = sum(item.produto.preco * item.quantidade for item in sacola.itens)
        taxa_entrega = restaurante.taxa_entrega or 0.0
        total = subtotal + taxa_entrega

        # Cria o pedido
        pedido = Pedido(
            usuario_id=usuario_id,
            restaurante_id=sacola.restaurante_id,
            endereco_id=endereco_id,
            forma_pagamento=forma_pagamento,
            status=StatusPedido.AGUARDANDO_CONFIRMACAO,
            subtotal=round(subtotal, 2),
            taxa_entrega=round(taxa_entrega, 2),
            total=round(total, 2),
            observacao=observacao,
        )
        db.session.add(pedido)
        db.session.flush()  # gera pedido.id antes de criar os itens

        # Copia os itens da sacola como snapshot imutável
        for item in sacola.itens:
            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                produto_id=item.produto_id,
                nome_produto=item.produto.nome,
                preco_unitario=item.produto.preco,
                quantidade=item.quantidade,
                observacao=item.observacao,
                subtotal_item=round(item.produto.preco * item.quantidade, 2),
            )
            db.session.add(item_pedido)

        # Limpa a sacola após confirmação
        db.session.delete(sacola)

        try:
            db.session.commit()
            return pedido, None, 201
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao criar pedido: {str(exc)}", 500

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    @staticmethod
    def buscar(pedido_id: int, usuario_id: int):
        """Busca um pedido pelo ID. Usuário só pode ver seus próprios pedidos."""
        pedido = db.session.get(Pedido, pedido_id)
        if not pedido:
            return None, "Pedido não encontrado", 404
        if pedido.usuario_id != usuario_id:
            return None, "Acesso negado", 403
        return pedido, None, 200

    @staticmethod
    def listar_por_usuario(usuario_id: int):
        """Lista todos os pedidos do usuário, do mais recente ao mais antigo."""
        pedidos = (
            Pedido.query
            .filter_by(usuario_id=usuario_id)
            .order_by(Pedido.criado_em.desc())
            .all()
        )
        return pedidos, None, 200

    @staticmethod
    def listar_por_restaurante(restaurante_id: int):
        """Lista todos os pedidos recebidos pelo restaurante."""
        pedidos = (
            Pedido.query
            .filter_by(restaurante_id=restaurante_id)
            .order_by(Pedido.criado_em.desc())
            .all()
        )
        return pedidos, None, 200

    # ------------------------------------------------------------------
    # Atualização de status (restaurante)
    # ------------------------------------------------------------------

    @staticmethod
    def avancar_status(pedido_id: int, restaurante_id: int):
        """
        Avança o status do pedido para o próximo na sequência.
        Só o restaurante dono do pedido pode chamar.
        """
        pedido = db.session.get(Pedido, pedido_id)
        if not pedido:
            return None, "Pedido não encontrado", 404
        if pedido.restaurante_id != restaurante_id:
            return None, "Acesso negado: pedido não pertence a este restaurante", 403

        proximo = _TRANSICOES_RESTAURANTE.get(pedido.status)
        if not proximo:
            return None, f"Pedido já está com status '{pedido.status.value}' e não pode avançar", 400

        pedido.status = proximo

        try:
            db.session.commit()
            return pedido, None, 200
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar status: {str(exc)}", 500

    @staticmethod
    def cancelar(pedido_id: int, usuario_id: int):
        """
        Cancela o pedido. Permitido apenas se ainda estiver
        AGUARDANDO_CONFIRMACAO ou CONFIRMADO.
        """
        pedido = db.session.get(Pedido, pedido_id)
        if not pedido:
            return None, "Pedido não encontrado", 404
        if pedido.usuario_id != usuario_id:
            return None, "Acesso negado", 403

        cancelaveis = {StatusPedido.AGUARDANDO_CONFIRMACAO, StatusPedido.CONFIRMADO}
        if pedido.status not in cancelaveis:
            return None, f"Não é possível cancelar um pedido com status '{pedido.status.value}'", 400

        pedido.status = StatusPedido.CANCELADO

        try:
            db.session.commit()
            return pedido, None, 200
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao cancelar pedido: {str(exc)}", 500
