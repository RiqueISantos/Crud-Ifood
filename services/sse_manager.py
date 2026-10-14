"""
sse_manager.py — Gerenciador de conexões Server-Sent Events.

Mantém uma lista de filas por pedido_id.
Quando o simulador avança o status, chama `emitir()` e todos os
clientes ouvindo aquele pedido recebem o evento instantaneamente.
"""

import queue
import threading

# { pedido_id (int): [Queue, Queue, ...] }
_listeners: dict[int, list[queue.Queue]] = {}
_lock = threading.Lock()


def registrar(pedido_id: int) -> queue.Queue:
    """Cria e registra uma fila para um novo cliente ouvindo o pedido."""
    fila = queue.Queue()
    with _lock:
        if pedido_id not in _listeners:
            _listeners[pedido_id] = []
        _listeners[pedido_id].append(fila)
    return fila


def remover(pedido_id: int, fila: queue.Queue):
    """Remove a fila quando o cliente desconecta."""
    with _lock:
        if pedido_id in _listeners:
            try:
                _listeners[pedido_id].remove(fila)
            except ValueError:
                pass
            if not _listeners[pedido_id]:
                del _listeners[pedido_id]


def emitir(pedido_id: int, dados: dict):
    """
    Envia um evento para todos os clientes ouvindo o pedido.
    Chamado pelo simulador após cada avanço de status.
    """
    with _lock:
        filas = list(_listeners.get(pedido_id, []))

    for fila in filas:
        try:
            fila.put_nowait(dados)
        except queue.Full:
            pass
