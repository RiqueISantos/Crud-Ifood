import os
import re
import secrets
import time
import requests
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app.models.models import CodigoVerificacao

load_dotenv()

CODIGO_TTL_SEGUNDOS = int(os.getenv("VERIFICATION_CODE_EXPIRY", "300"))
VERIFICACAO_TTL_SEGUNDOS = int(os.getenv("VERIFICATION_SESSION_EXPIRY", "900"))


class OtpService:

    def __init__(self):
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_template_sid = os.getenv("TWILIO_TEMPLATE_SID", "")
        self.whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "")
        
        self.twilio_client = None
        if all([self.twilio_account_sid, self.twilio_auth_token]):
            self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)

        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "")
        self.from_name = "iFood Clone"

    def _normalizar_destino(self, destino: str, canal: str) -> str:
        destino = destino.strip()
        if canal in ("sms", "whatsapp"):
            apenas_numeros = re.sub(r"\D", "", destino)
            if not apenas_numeros.startswith("55"):
                apenas_numeros = "55" + apenas_numeros
            return f"+{apenas_numeros}"
        elif canal == "email":
            email = destino.lower()
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
                raise ValueError("E-mail inválido.")
            return email
        raise ValueError(f"Canal '{canal}' não suportado.")

    def _disparar_externo(self, destino: str, codigo: str, canal: str):
        if canal in ("sms", "whatsapp"):
            if not self.twilio_client or not self.whatsapp_from or not self.twilio_template_sid:
                raise ValueError("Credenciais da Twilio incompletas.")
            self.twilio_client.messages.create(
                from_=f"whatsapp:{self.whatsapp_from}",
                to=f"whatsapp:{destino}",
                content_sid=self.twilio_template_sid,
                content_variables=f'{{"1": "{codigo}"}}'
            )
            print(f"[Twilio] Código enviado para {destino}")

        elif canal == "email":
            if not self.sendgrid_api_key or not self.from_email:
                print(f"[DEV] Código de e-mail para {destino}: {codigo}")
                return

            html = f"""
            <div style="font-family:Inter,sans-serif;max-width:480px;margin:auto;padding:32px;
                        background:#fff;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.08)">
              <div style="text-align:center;margin-bottom:24px">
                <span style="font-size:28px;font-weight:800;color:#EA1D2C">iFood</span>
              </div>
              <h2 style="color:#212121;font-size:20px;margin-bottom:8px">Código de verificação</h2>
              <p style="color:#616161;margin-bottom:24px">Use o código abaixo para autenticar sua conta.</p>
              <div style="text-align:center;background:#f9f9f9;border-radius:8px;padding:20px;margin-bottom:24px">
                <span style="font-size:36px;font-weight:700;letter-spacing:8px;color:#EA1D2C">{codigo}</span>
              </div>
              <p style="color:#9e9e9e;font-size:13px">
                Este código expira em {CODIGO_TTL_SEGUNDOS // 60} minutos.
              </p>
            </div>
            """
            payload = {
                "personalizations": [{"to": [{"email": destino}]}],
                "from": {"email": self.from_email, "name": self.from_name},
                "subject": "Seu código de acesso",
                "content": [
                    {"type": "text/plain", "value": f"Seu código: {codigo}"},
                    {"type": "text/html", "value": html}
                ]
            }
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {self.sendgrid_api_key}", "Content-Type": "application/json"},
                timeout=10
            )
            if resp.status_code not in (200, 202):
                raise ValueError(f"SendGrid erro {resp.status_code}: {resp.text}")
            print(f"[SendGrid] E-mail enviado para {destino}")

    def enviar_verificacao(self, destino_bruto: str, canal: str, db) -> str:
        destino = self._normalizar_destino(destino_bruto, canal)
        codigo = f"{secrets.randbelow(1_000_000):06d}"

        db.query(CodigoVerificacao).filter(
            CodigoVerificacao.destino == destino,
            CodigoVerificacao.canal == canal
        ).delete(synchronize_session=False)

        registro = CodigoVerificacao(
            destino=destino,
            canal=canal,
            codigo=codigo,
            expira_em=time.time() + CODIGO_TTL_SEGUNDOS,
            verificado=False,
            verificado_expira_em=None
        )
        db.add(registro)
        db.commit()

        # Dispara mensagem externa
        self._disparar_externo(destino, codigo, canal)
        return codigo

    def verificar_codigo(self, destino_bruto: str, codigo: str, canal: str, db) -> bool:
        destino = self._normalizar_destino(destino_bruto, canal)

        registro = (
            db.query(CodigoVerificacao)
            .filter(
                CodigoVerificacao.destino == destino,
                CodigoVerificacao.canal == canal,
                CodigoVerificacao.verificado == False
            )
            .order_by(CodigoVerificacao.expira_em.desc())
            .first()
        )

        if not registro:
            return False

        if time.time() > registro.expira_em:
            db.delete(registro)
            db.commit()
            return False

        if not secrets.compare_digest(registro.codigo, str(codigo).strip()):
            return False

        registro.verificado = True
        registro.verificado_expira_em = time.time() + VERIFICACAO_TTL_SEGUNDOS
        db.commit()
        return True

    def esta_verificado(self, destino_bruto: str, canal: str, db) -> bool:
        destino = self._normalizar_destino(destino_bruto, canal)

        registro = (
            db.query(CodigoVerificacao)
            .filter(
                CodigoVerificacao.destino == destino,
                CodigoVerificacao.canal == canal,
                CodigoVerificacao.verificado == True
            )
            .order_by(CodigoVerificacao.verificado_expira_em.desc())
            .first()
        )

        if not registro or not registro.verificado_expira_em:
            return False

        if time.time() > registro.verificado_expira_em:
            db.delete(registro)
            db.commit()
            return False

        return True

    def invalidar_verificacao(self, destino_bruto: str, canal: str, db) -> None:
        destino = self._normalizar_destino(destino_bruto, canal)
        db.query(CodigoVerificacao).filter(
            CodigoVerificacao.destino == destino,
            CodigoVerificacao.canal == canal
        ).delete(synchronize_session=False)
        db.commit()