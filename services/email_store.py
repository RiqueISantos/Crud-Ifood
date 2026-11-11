"""
email_store.py — Envia e valida códigos de verificação por e-mail via SendGrid.
"""

import os
import random
import threading
import time

from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY  = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM     = os.getenv("SENDGRID_FROM_EMAIL", "emailverificacaoifood@gmail.com")
OTP_EXPIRY        = int(os.getenv("EMAIL_VERIFICATION_EXPIRY", "300"))

# Store thread-safe: { email: { "codigo": str, "expira": float } }
_store: dict = {}
_lock = threading.Lock()


def enviar_codigo_email(email: str) -> tuple:
    """
    Gera e envia código de verificação por e-mail.
    Retorna (True, codigo) ou (False, mensagem_erro).
    """
    codigo = str(random.randint(100000, 999999))
    expira = time.time() + OTP_EXPIRY

    with _lock:
        _store[email] = {"codigo": codigo, "expira": expira}

    if not SENDGRID_API_KEY:
        print(f"[EMAIL DEV] {email} → {codigo}")
        return True, codigo

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        message = Mail(
            from_email=SENDGRID_FROM,
            to_emails=email,
            subject="Seu código de verificação iFood",
            html_content=f"""
                <div style="font-family:sans-serif;max-width:480px;margin:auto">
                  <h2 style="color:#ea1d2c">Código de verificação</h2>
                  <p>Use o código abaixo para confirmar seu e-mail:</p>
                  <div style="font-size:2rem;font-weight:700;letter-spacing:8px;color:#ea1d2c;margin:24px 0">
                    {codigo}
                  </div>
                  <p style="color:#666;font-size:0.85rem">
                    Válido por {OTP_EXPIRY // 60} minutos. Não compartilhe este código.
                  </p>
                </div>
            """,
        )
        sg.send(message)
        return True, codigo
    except Exception as e:
        print(f"[EMAIL] Erro SendGrid: {e}")
        return False, str(e)


def verificar_codigo_email(email: str, codigo: str) -> tuple:
    """
    Valida o código de e-mail. Retorna (True, "ok") ou (False, mensagem_erro).
    """
    with _lock:
        entrada = _store.get(email)
        if not entrada:
            return False, "Código não encontrado. Solicite um novo."
        if time.time() > entrada["expira"]:
            del _store[email]
            return False, "Código expirado. Solicite um novo."
        if entrada["codigo"] != codigo.strip():
            return False, "Código inválido. Verifique e tente novamente."
        del _store[email]
        return True, "ok"


# Mensagens e emojis para cada status do pedido
_STATUS_INFO = {
    "AGUARDANDO_CONFIRMACAO": ("⏳ Pedido recebido",          "Seu pedido foi recebido e está aguardando confirmação do restaurante."),
    "CONFIRMADO":             ("✅ Pedido confirmado",         "O restaurante confirmou seu pedido e já vai começar o preparo!"),
    "EM_PREPARACAO":          ("👨‍🍳 Pedido em preparo",         "Seu pedido está sendo preparado com carinho pelo restaurante."),
    "SAIU_PARA_ENTREGA":      ("🛵 Pedido saiu para entrega", "Seu pedido está a caminho! O entregador já está indo até você."),
    "ENTREGUE":               ("🎉 Pedido entregue",           "Seu pedido foi entregue. Bom apetite!"),
    "CANCELADO":              ("❌ Pedido cancelado",          "Seu pedido foi cancelado. Em caso de dúvidas, entre em contato."),
}


def enviar_notificacao_status(email: str, nome: str, pedido_id: int, status: str) -> None:
    """
    Envia e-mail notificando o usuário sobre a mudança de status do pedido.
    Chamado automaticamente pelo simulador a cada transição.
    """
    info = _STATUS_INFO.get(status)
    if not info:
        return

    titulo, descricao = info

    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:480px;margin:auto;padding:28px;
                background:#fff;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.08)">
      <div style="text-align:center;margin-bottom:16px">
        <span style="font-size:26px;font-weight:800;color:#EA1D2C">iFood</span>
      </div>
      <h2 style="color:#212121;font-size:18px;margin-bottom:8px">{titulo}</h2>
      <p style="color:#616161;margin-bottom:16px">
        Olá, <strong>{nome}</strong>! Atualização do seu pedido <strong>#{pedido_id}</strong>:
      </p>
      <div style="background:#fff8f8;border-left:4px solid #EA1D2C;
                  padding:12px 16px;border-radius:0 8px 8px 0;margin-bottom:20px">
        <p style="color:#212121;margin:0;font-size:15px">{descricao}</p>
      </div>
      <p style="color:#9e9e9e;font-size:12px;text-align:center">
        iFood Clone — acompanhe seu pedido em tempo real pelo app.
      </p>
    </div>
    """

    if not SENDGRID_API_KEY:
        print(f"[EMAIL DEV] Notificação status '{status}' para {email} (pedido {pedido_id})")
        return

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        message = Mail(
            from_email=SENDGRID_FROM,
            to_emails=email,
            subject=f"{titulo} — Pedido #{pedido_id}",
            html_content=html,
        )
        sg.send(message)
        print(f"[EMAIL] Notificação '{status}' enviada para {email} (pedido {pedido_id})")
    except Exception as e:
        print(f"[EMAIL] Erro ao enviar notificação de status: {e}")
