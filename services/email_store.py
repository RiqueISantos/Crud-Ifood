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
