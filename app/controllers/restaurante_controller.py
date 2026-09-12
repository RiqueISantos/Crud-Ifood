from ..database import db
from ..models.models import Restaurante
from services.service_endereco import EnderecoService


class RestauranteController:

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _preencher_endereco_via_cep(restaurante: Restaurante, dados: dict):
        """
        Consulta o ViaCEP com o CEP informado e preenche os campos de endereço
        diretamente no objeto Restaurante. Retorna (erro, status_code) ou (None, None).
        """
        cep = dados.get("cep")
        if not cep:
            return "Campo 'cep' é obrigatório", 400

        try:
            dados_cep = EnderecoService.consultar_viacep(cep)
        except ValueError as err:
            return str(err), 400
        except RuntimeError as err:
            return str(err), 502

        # Logradouro pode vir do ViaCEP ou, em cidades com CEP único, do payload
        logradouro = (dados_cep.get("logradouro") or dados.get("logradouro") or "").strip()
        if not logradouro:
            return (
                "Para cidades com CEP geral, informe o nome da rua/avenida no campo 'logradouro'",
                400,
            )

        bairro = (dados_cep.get("bairro") or dados.get("bairro") or "Centro").strip()

        restaurante.cep = dados_cep["cep"]
        restaurante.logradouro = logradouro
        restaurante.bairro = bairro
        restaurante.cidade = dados_cep["cidade"]
        restaurante.uf = dados_cep["uf"]
        restaurante.numero = str(dados.get("numero", "")).strip()
        restaurante.complemento = (dados.get("complemento") or "").strip() or None

        # Coordenadas via AwesomeAPI / Nominatim
        lat, lng = EnderecoService.obter_coordenadas(
            logradouro=restaurante.logradouro,
            numero=restaurante.numero,
            bairro=restaurante.bairro,
            cidade=restaurante.cidade,
            uf=restaurante.uf,
            cep=dados_cep["cep"],
        )
        restaurante.latitude = lat
        restaurante.longitude = lng

        return None, None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def criar(dados: dict):
        """Valida e persiste um novo restaurante."""
        campos_obrigatorios = ["nome", "email", "telefone", "categoria_principal", "cep", "numero"]
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return None, f"Campo '{campo}' é obrigatório", 400

        if Restaurante.query.filter_by(email=dados["email"]).first():
            return None, "E-mail já cadastrado", 409

        restaurante = Restaurante(
            nome=dados["nome"],
            email=dados["email"],
            telefone=dados["telefone"],
            categoria_principal=dados["categoria_principal"],
            taxa_entrega=dados.get("taxa_entrega"),
            tempo_estimado=dados.get("tempo_estimado"),
            # Campos de endereço serão preenchidos abaixo via ViaCEP
            logradouro="",
            numero="",
            bairro="",
            cidade="",
            uf="",
            cep="",
        )

        erro, status = RestauranteController._preencher_endereco_via_cep(restaurante, dados)
        if erro:
            return None, erro, status

        try:
            db.session.add(restaurante)
            db.session.commit()
            return restaurante, None, 201
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao persistir restaurante: {str(exc)}", 500

    @staticmethod
    def listar():
        """Retorna todos os restaurantes cadastrados."""
        restaurantes = Restaurante.query.all()
        return restaurantes, None, 200

    @staticmethod
    def buscar(id: int):
        """Busca um restaurante pelo ID."""
        restaurante = db.session.get(Restaurante, id)
        if not restaurante:
            return None, "Restaurante não encontrado", 404
        return restaurante, None, 200

    @staticmethod
    def atualizar(id: int, dados: dict):
        """
        Atualiza os dados de um restaurante existente.
        Se o CEP for informado, revalida via ViaCEP e recalcula coordenadas.
        """
        restaurante = db.session.get(Restaurante, id)
        if not restaurante:
            return None, "Restaurante não encontrado", 404

        if not dados:
            return None, "Dados não fornecidos", 400

        # Campos simples
        if dados.get("nome"):
            restaurante.nome = dados["nome"]

        if dados.get("categoria_principal"):
            restaurante.categoria_principal = dados["categoria_principal"]

        if "taxa_entrega" in dados:
            restaurante.taxa_entrega = dados["taxa_entrega"]

        if dados.get("tempo_estimado"):
            restaurante.tempo_estimado = dados["tempo_estimado"]

        # Email — verifica duplicidade
        if dados.get("email") and dados["email"] != restaurante.email:
            existente = Restaurante.query.filter_by(email=dados["email"]).first()
            if existente and existente.id != id:
                return None, "E-mail já cadastrado por outro restaurante", 409
            restaurante.email = dados["email"]

        # Telefone
        if dados.get("telefone"):
            restaurante.telefone = dados["telefone"]

        # Endereço — qualquer alteração de CEP ou número dispara nova consulta ao ViaCEP
        novo_cep = dados.get("cep")
        novo_numero = dados.get("numero")

        cep_mudou = novo_cep and novo_cep.replace("-", "") != restaurante.cep.replace("-", "")
        numero_mudou = novo_numero and str(novo_numero).strip() != restaurante.numero

        if cep_mudou or numero_mudou:
            # Garante que o dict de dados tenha o CEP mais atualizado para o helper
            if not cep_mudou:
                dados["cep"] = restaurante.cep
            if not numero_mudou:
                dados["numero"] = restaurante.numero

            erro, status = RestauranteController._preencher_endereco_via_cep(restaurante, dados)
            if erro:
                return None, erro, status
        else:
            # Permite atualizar campos opcionais de endereço sem re-consultar o CEP
            if dados.get("complemento") is not None:
                restaurante.complemento = (dados["complemento"] or "").strip() or None

        try:
            db.session.commit()
            return restaurante, None, 200
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar restaurante: {str(exc)}", 500

    @staticmethod
    def deletar(id: int):
        """Remove um restaurante pelo ID."""
        restaurante = db.session.get(Restaurante, id)
        if not restaurante:
            return None, "Restaurante não encontrado", 404

        try:
            db.session.delete(restaurante)
            db.session.commit()
            return {"mensagem": f"Restaurante {id} deletado com sucesso"}, None, 200
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao deletar restaurante: {str(exc)}", 500
