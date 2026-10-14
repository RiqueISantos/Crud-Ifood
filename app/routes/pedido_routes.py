from flask import Blueprint, request, jsonify, Response, stream_with_context
from services.auth import jwt_required, verificar_token_jwt
from services.sse_manager import registrar, remover
from ..controllers.pedido_controller import PedidoController
from ..models.models import StatusPedido, FormaPagamento, Sacola, Endereco, Pedido
from ..database import db
import json
import queue

pedido_bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")


def serializar_pedido(pedido):
    """Serializa um Pedido completo com seus itens."""
    return {
        "id":              pedido.id,
        "status":          pedido.status.value,
        "forma_pagamento": pedido.forma_pagamento.value if pedido.forma_pagamento else None,
        "observacao":      pedido.observacao,
        "gateway_pagamento_id": pedido.gateway_pagamento_id, 
        "url_pagamento":   pedido.url_pagamento,
        "restaurante": {
            "id":   pedido.restaurante.id,
            "nome": pedido.restaurante.nome,
        } if pedido.restaurante else None,
        "endereco": {
            "id":          pedido.endereco.id,
            "logradouro":  pedido.endereco.logradouro,
            "numero":      pedido.endereco.numero,
            "complemento": pedido.endereco.complemento,
            "bairro":      pedido.endereco.bairro,
            "cidade":      pedido.endereco.cidade,
            "uf":          pedido.endereco.uf,
        } if pedido.endereco else None,
        "itens": [
            {
                "id":             item.id,
                "produto_id":     item.produto_id,
                "nome_produto":   item.nome_produto,
                "preco_unitario": item.preco_unitario,
                "quantidade":     item.quantidade,
                "observacao":     item.observacao,
                "subtotal_item":  item.subtotal_item,
            }
            for item in pedido.itens
        ],
        "subtotal":     pedido.subtotal,
        "taxa_entrega": pedido.taxa_entrega,
        "total":        pedido.total,
        "criado_em":    pedido.criado_em.isoformat() if pedido.criado_em else None,
        "atualizado_em": pedido.atualizado_em.isoformat() if pedido.atualizado_em else None,
    }


# ── Usuário ───────────────────────────────────────────────────────────────────

@pedido_bp.route("/confirmar", methods=["POST"])
@jwt_required
def confirmar_pedido(usuario_id):
    dados = request.get_json() or {}
    
    if not dados.get("endereco_id"):
        return jsonify({"erro": "O ID do endereço é obrigatório"}), 400

    pedido, erro, status = PedidoController.confirmar(usuario_id, dados)
    
    if erro:
        return jsonify({"erro": f"Erro no controller: {erro}"}), status
        
    return jsonify(serializar_pedido(pedido)), status

@pedido_bp.route("/meus", methods=["GET"])
@jwt_required
def listar_meus_pedidos(usuario_id):
    """Lista todos os pedidos do usuário autenticado."""
    pedidos, erro, status = PedidoController.listar_por_usuario(usuario_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify([serializar_pedido(p) for p in pedidos]), status


@pedido_bp.route("/<int:pedido_id>", methods=["GET"])
@jwt_required
def buscar_pedido(pedido_id, usuario_id):
    """Busca os detalhes de um pedido específico do usuário."""
    pedido, erro, status = PedidoController.buscar(pedido_id, usuario_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(serializar_pedido(pedido)), status


@pedido_bp.route("/<int:pedido_id>/cancelar", methods=["PATCH"])
@jwt_required
def cancelar_pedido(pedido_id, usuario_id):
    """
    Cancela o pedido. Permitido apenas nos status:
    AGUARDANDO_CONFIRMACAO ou CONFIRMADO.
    """
    pedido, erro, status = PedidoController.cancelar(pedido_id, usuario_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(serializar_pedido(pedido)), status


# ── Restaurante ───────────────────────────────────────────────────────────────

@pedido_bp.route("/restaurante", methods=["GET"])
@jwt_required
def listar_pedidos_restaurante(usuario_id):
    """
    Lista todos os pedidos recebidos pelo restaurante autenticado.
    O JWT aqui deve ser do restaurante.
    """
    pedidos, erro, status = PedidoController.listar_por_restaurante(usuario_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify([serializar_pedido(p) for p in pedidos]), status


@pedido_bp.route("/<int:pedido_id>/status", methods=["PATCH"])
@jwt_required
def avancar_status(pedido_id, usuario_id):
    """
    Avança o status do pedido para o próximo na sequência.
    JWT deve ser do restaurante dono do pedido.
    """
    # O 'usuario_id' aqui representa o dono do restaurante logado
    pedido, erro, status = PedidoController.avancar_status(pedido_id, usuario_id)
    if erro:
        return jsonify({"erro": erro}), status
    return jsonify(serializar_pedido(pedido)), status


# ── Utilitário ────────────────────────────────────────────────────────────────

@pedido_bp.route("/status/opcoes", methods=["GET"])
def listar_status():
    """Retorna todos os status e formas de pagamento disponíveis."""
    return jsonify({
        "status":            [s.value for s in StatusPedido],
        "formas_pagamento":  [f.value for f in FormaPagamento],
    }), 200

# ── SSE — Acompanhamento em tempo real ───────────────────────────────────────

@pedido_bp.route("/<int:pedido_id>/acompanhar", methods=["GET"])
def acompanhar_pedido(pedido_id):
    """
    Abre uma conexão SSE para acompanhar o pedido em tempo real.

    Autenticação via query param (SSE não suporta headers customizados):
      GET /pedidos/1/acompanhar?token=<access_token>

    O frontend consome assim:
      const es = new EventSource('/pedidos/1/acompanhar?token=SEU_TOKEN')
      es.onmessage = (e) => {
        const { status } = JSON.parse(e.data)
        // atualiza a UI
      }
    """
    # Valida o JWT via query param (SSE não permite Authorization header)
    token = request.args.get("token", "")
    if not token:
        return jsonify({"erro": "Token é obrigatório"}), 401

    try:
        payload = verificar_token_jwt(token)
        usuario_id = int(payload["sub"])
    except Exception:
        return jsonify({"erro": "Token inválido ou expirado"}), 401

    # Verifica se o pedido pertence ao usuário
    pedido = db.session.get(Pedido, pedido_id)
    if not pedido:
        return jsonify({"erro": "Pedido não encontrado"}), 404
    if pedido.usuario_id != usuario_id:
        return jsonify({"erro": "Acesso negado"}), 403

    def stream():
        fila = registrar(pedido_id)

        # Envia o status atual imediatamente ao conectar
        yield f"data: {json.dumps({'status': pedido.status.value, 'pedido_id': pedido_id})}\n\n"

        try:
            while True:
                try:
                    # Aguarda próximo evento com timeout de 25s (keepalive)
                    evento = fila.get(timeout=25)
                    yield f"data: {json.dumps(evento)}\n\n"

                    # Fecha a conexão quando o pedido for finalizado
                    if evento.get("status") in ("ENTREGUE", "CANCELADO"):
                        break

                except queue.Empty:
                    # Keepalive — evita que proxies fechem a conexão por inatividade
                    yield ": keepalive\n\n"
        finally:
            remover(pedido_id, fila)

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # desativa buffer do Nginx se houver
        },
    )


# ── Webhook Asaas ─────────────────────────────────────────────────────────────

@pedido_bp.route("/webhook/asaas", methods=["POST"])
def webhook_asaas():
    dados = request.get_json()

    if dados and dados.get("event") == "PAYMENT_RECEIVED":
        # O Asaas devolve o ID do nosso pedido dentro de "externalReference"
        pedido_id = dados.get("payment", {}).get("externalReference")
        
        if pedido_id:
            pedido = Pedido.query.get(pedido_id)
            if pedido:
                pedido.status = "AGUARDANDO_CONFIRMACAO"
                db.session.commit()
                return jsonify({"status": "Webhook processado com sucesso"}), 200
                
    return jsonify({"status": "Evento ignorado ou dados inválidos"}), 200