"""
otp_store.py — Envia e valida códigos OTP via Twilio WhatsApp.
"""

import os
import random
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_store: dict = {}
_lock = threading.Lock()


def _to_whatsapp(telefone: str) -> str:
    """Normaliza para whatsapp:+55XXXXXXXXXXX"""
    digits = "".join(c for c in telefone if c.isdigit())
    if not digits.startswith("55"):
        digits = "55" + digits
    return f"whatsapp:+{digits}"


def enviar_otp(telefone: str) -> tuple:
    """Gera, armazena e envia OTP via Twilio WhatsApp."""
    
    account_sid  = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token   = os.getenv("TWILIO_AUTH_TOKEN")
    template_sid = os.getenv("TWILIO_TEMPLATE_SID")
    from_number  = os.getenv("TWILIO_WHATSAPP_FROM", "+14155238886")
    expiry       = int(os.getenv("EMAIL_VERIFICATION_EXPIRY", "300"))

    if not account_sid or not auth_token:
        return False, "Credenciais Twilio não configuradas"

    codigo = str(random.randint(100000, 999999))

    with _lock:
        _store[telefone] = {"codigo": codigo, "expira": time.time() + expiry}

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        client.messages.create(
            from_=f"whatsapp:{from_number}",
            to=_to_whatsapp(telefone),
            content_sid=template_sid,
            content_variables=f'{{"1":"{codigo}"}}',
        )
        return True, "Código enviado via WhatsApp"
    except Exception as e:
        print(f"[OTP] Erro Twilio: {e}")
        return False, str(e)


def verificar_otp(telefone: str, codigo: str) -> tuple:
    """Valida o código. Retorna (True, 'ok') ou (False, mensagem_erro)."""
    with _lock:
        entrada = _store.get(telefone)
        if not entrada:
            return False, "Código não encontrado. Solicite um novo."
        if time.time() > entrada["expira"]:
            del _store[telefone]
            return False, "Código expirado. Solicite um novo."
        if entrada["codigo"] != codigo.strip():
            return False, "Código inválido. Verifique e tente novamente."
        del _store[telefone]
        return True, "ok"
