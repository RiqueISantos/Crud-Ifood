"""
simulador_pedido.py — Avança o status do pedido automaticamente com delays.

Simula o fluxo real de um pedido sem precisar de ação manual do restaurante.
Os tempos abaixo podem ser ajustados livremente.

Fluxo para pagamento em dinheiro/vale:
  AGUARDANDO_CONFIRMACAO → CONFIRMADO → EM_PREPARACAO → SAIU_PARA_ENTREGA → ENTREGUE

Fluxo para PIX/cartão (simulado — ignora gateway real):
  AGUARDANDO_PAGAMENTO → AGUARDANDO_CONFIRMACAO → CONFIRMADO → EM_PREPARACAO → SAIU_PARA_ENTREGA → ENTREGUE
"""

from datetime import datetime, timedelta, timezone

# Delay acumulado em minutos a partir da criação do pedido
_SEQUENCIA = [
    # (status_esperado,          proximo_status,          minutos_desde_criacao)
    ("AGUARDANDO_PAGAMENTO",   "AGUARDANDO_CONFIRMACAO", 1),
    ("AGUARDANDO_CONFIRMACAO", "CONFIRMADO",             2),
    ("CONFIRMADO",             "EM_PREPARACAO",          4),
    ("EM_PREPARACAO",          "SAIU_PARA_ENTREGA",      7),
    ("SAIU_PARA_ENTREGA",      "ENTREGUE",               10),
]


def _avancar_status_pedido(app, pedido_id: int, status_esperado: str, proximo_status: str):
    """
    Executado pelo scheduler no momento agendado.
    Só avança se o pedido ainda estiver no status esperado —
    protege contra cancelamentos que ocorram no meio do caminho.
    """
    with app.app_context():
        from app.database import db
        from app.models.models import Pedido, StatusPedido

        pedido = db.session.get(Pedido, pedido_id)
        if not pedido:
            return

        if pedido.status == StatusPedido.CANCELADO:
            return

        if pedido.status.value != status_esperado:
            return

        try:
            pedido.status = StatusPedido[proximo_status]
            db.session.commit()
            print(f"[Simulador] Pedido {pedido_id}: {status_esperado} → {proximo_status}")

            # Notifica clientes SSE em tempo real
            from services.sse_manager import emitir
            emitir(pedido_id, {
                "status": proximo_status,
                "pedido_id": pedido_id,
            })
        except Exception as exc:
            db.session.rollback()
            print(f"[Simulador] Erro ao avançar pedido {pedido_id}: {exc}")


def simular_progresso(scheduler, app, pedido_id: int, status_inicial: str):
    """
    Agenda todas as transições de status a partir do status_inicial do pedido.

    Parâmetros:
      scheduler     — instância do APScheduler (importado do app)
      app           — instância do Flask app (para app_context nas tasks)
      pedido_id     — ID do pedido recém-criado
      status_inicial — "AGUARDANDO_PAGAMENTO" ou "AGUARDANDO_CONFIRMACAO"
    """
    agora = datetime.now(tz=timezone.utc)

    # Filtra apenas as etapas a partir do status_inicial
    ativo = False
    for status_esperado, proximo_status, minutos in _SEQUENCIA:
        if status_esperado == status_inicial:
            ativo = True

        if not ativo:
            continue

        run_at = agora + timedelta(minutes=minutos)

        scheduler.add_job(
            func=_avancar_status_pedido,
            trigger="date",
            run_date=run_at,
            args=[app, pedido_id, status_esperado, proximo_status],
            id=f"pedido_{pedido_id}_{status_esperado}",
            replace_existing=True,
        )

    print(f"[Simulador] Progresso agendado para pedido {pedido_id} "
          f"a partir de '{status_inicial}' (até 10 min)")
