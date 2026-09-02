from sqlalchemy.orm import Session
from app.models.models import Usuario
from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
class UsuarioController:

    def __init__(self, db: Session, sms_service=None, email_service=None):
        self.db = db
        self.services = {
            "sms": sms_service,
            "whatsapp": sms_service,
            "email": email_service
        }

    def _obter_servico(self, canal: str):
        servico = self.services.get(canal.lower())
        if not servico:
            raise ValueError(f"Serviço de envio para o canal '{canal}' não configurado.")
        return servico

    def enviar_codigo(self, destino: str, canal: str, tipo_fluxo="cadastro") -> None:
        usuario = self.db.query(Usuario).filter(
            (Usuario.email == destino) | (Usuario.telefone == destino)
        ).first()

        if tipo_fluxo == "login" and not usuario:
            raise ValueError("Usuário não encontrado.")
        if tipo_fluxo == "cadastro" and usuario:
            raise ValueError("Contato já cadastrado no sistema.")

        servico = self._obter_servico(canal)
        servico.enviar_verificacao(destino, canal, self.db)

    def verificar_codigo(self, destino: str, codigo: str, canal: str) -> None:
        servico = self._obter_servico(canal)
        if not servico.verificar_codigo(destino, codigo, canal, self.db):
            raise ValueError("Código inválido ou expirado.")

    def autenticar_login(self, identificador: str, codigo: str, canal: str) -> Usuario:
        self.verificar_codigo(identificador, codigo, canal)
        
        usuario = self.db.query(Usuario).filter(
            (Usuario.email == identificador) | (Usuario.telefone == identificador)
        ).first()

        if not usuario:
            raise ValueError("Usuário não encontrado.")
        return usuario

    def criar_usuario(self, dados: dict) -> Usuario:
        servico_wpp = self._obter_servico("sms")
        servico_email = self._obter_servico("email")

        if servico_wpp and not servico_wpp.esta_verificado(dados["telefone"], "sms", self.db):
            raise ValueError("Celular não verificado.")
        
        if servico_email and not servico_email.esta_verificado(dados["email"], "email", self.db):
            raise ValueError("E-mail não verificado.")

        usuario = Usuario(
            nome=dados.get("nome"),
            email=dados.get("email"),
            telefone=dados.get("telefone"),
            documento=dados.get("documento")
        )
        
        self.db.add(usuario)
        self.db.commit()
        
        if servico_wpp:
            servico_wpp.invalidar_verificacao(dados["telefone"], "whatsapp", self.db)
        if servico_email:
            servico_email.invalidar_verificacao(dados["email"], "email", self.db)

        return usuario

    def buscar(self, id: int) -> Usuario:
        usuario = self.db.get(Usuario, id)
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        return usuario

    def listar(self) -> list:
        return self.db.query(Usuario).all()

    def atualizar(self, id: int, dados: dict) -> Usuario:
        usuario = self.buscar(id)

        if dados.get("email"):
            novo_email = dados["email"].strip().lower()
            existente = self.db.query(Usuario).filter_by(email=novo_email).first()
            if existente and existente.id != id:
                raise ValueError("E-mail já cadastrado por outro usuário.")
            usuario.email = novo_email

        if dados.get("nome"):
            usuario.nome = dados["nome"].strip()
        if dados.get("telefone"):
            usuario.telefone = dados["telefone"].strip()
        if dados.get("documento"):
            usuario.documento = dados["documento"].strip()

        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def deletar(self, id: int) -> dict:
        usuario = self.buscar(id)
        self.db.delete(usuario)
        self.db.commit()
        return {"mensagem": f"Usuário {id} deletado com sucesso."}

    def autenticar_login_google(self, token_google: str) -> Usuario:
        """
        Valida o token JWT do Google, busca o usuário no banco de dados e,
        se não existir, realiza o cadastro automaticamente.
        """
        try:
            # 1. Valida o token com os servidores do Google
            idinfo = id_token.verify_oauth2_token(
                token_google, 
                requests.Request(), 
                GOOGLE_CLIENT_ID
            )
            
            email = idinfo.get("email")
            nome = idinfo.get("name")

            if not email:
                raise ValueError("O token do Google não contém um e-mail válido.")

            # 2. Busca o usuário pelo e-mail
            usuario = self.db.query(Usuario).filter(Usuario.email == email).first()

            # 3. Se o usuário não existir, cria um novo (Cadastro via Google)
            if not usuario:
                usuario = Usuario(
                    nome=nome,
                    email=email,
                    # Telefone e documento ficam vazios, o usuário pode preencher depois no perfil
                )
                self.db.add(usuario)
                self.db.commit()
                self.db.refresh(usuario)

            return usuario

        except ValueError as e:
            # Isso captura tokens inválidos, expirados ou o erro manual acima
            raise ValueError(f"Falha na autenticação com Google: {str(e)}")



    def autenticar_login_facebook(self, token_facebook: str) -> Usuario:
        """
        Valida o token do Facebook na Graph API, busca o usuário no banco e,
        se não existir, realiza o cadastro automaticamente.
        """
        try:
            # 1. Bate na API do Facebook pedindo o ID, Nome e E-mail desse token
            url = f"https://graph.facebook.com/me?access_token={token_facebook}&fields=id,name,email"
            resposta = req.get(url)
            dados_fb = resposta.json()

            # 2. Verifica se o token era inválido ou expirou
            if "error" in dados_fb:
                raise ValueError(f"Token do Facebook inválido: {dados_fb['error']['message']}")

            email = dados_fb.get("email")
            nome = dados_fb.get("name")

            # 3. O Facebook permite criar conta com celular (sem e-mail). 
            # Como seu sistema exige e-mail, precisamos travar isso.
            if not email:
                raise ValueError("O perfil do Facebook não compartilhou um e-mail válido.")

            # 4. Busca o usuário pelo e-mail
            usuario = self.db.query(Usuario).filter(Usuario.email == email).first()

            # 5. Se não existir, cadastra no banco
            if not usuario:
                usuario = Usuario(
                    nome=nome,
                    email=email
                    # Telefone e documento ficam vazios
                )
                self.db.add(usuario)
                self.db.commit()
                self.db.refresh(usuario)

            return usuario

        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Falha na autenticação com Facebook: {str(e)}")