from ..database import db
from ..models.models import Endereco, Usuario
from services.service_endereco import EnderecoService


class EnderecoController:

    @staticmethod
    def consultar_cep(cep: str):
        """Passo 1: Consulta o ViaCEP para pré-preencher o formulário no front."""
        try:
            dados_cep = EnderecoService.consultar_viacep(cep)
            return dados_cep, None, 200
        except ValueError as err:
            return None, str(err), 400
        except RuntimeError as err:
            return None, str(err), 502

    @staticmethod
    def salvar(dados: dict):
        """
        Passo 2: Valida dados, garante integridade cadastral e calcula coordenadas.
        Trata cidades com CEP único exigindo o logradouro caso o ViaCEP não forneça.
        """
        campos_obrigatorios = ["usuario_id", "cep", "numero"]
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return None, f"Campo '{campo}' é obrigatório", 400

        usuario = db.session.get(Usuario, dados["usuario_id"])
        if not usuario:
            return None, "Usuário informado não existe", 404

        try:
            dados_cep = EnderecoService.consultar_viacep(dados["cep"])
        except ValueError as err:
            return None, str(err), 400
        except RuntimeError as err:
            return None, str(err), 502

        logradouro = (dados_cep.get("logradouro") or dados.get("logradouro") or "").strip()
        bairro = (dados_cep.get("bairro") or dados.get("bairro") or "Centro").strip()
        cidade = dados_cep.get("cidade")
        uf = dados_cep.get("uf")
        numero = str(dados["numero"]).strip()

        if not logradouro:
            return None, "Para cidades com CEP geral, informe o nome da rua/avenida no campo 'logradouro'", 400

        lat, lng = EnderecoService.obter_coordenadas(
            logradouro=logradouro,
            numero=numero,
            bairro=bairro,       
            cidade=cidade,
            uf=uf,
            cep=dados_cep["cep"] 
        )

        endereco = Endereco(
            usuario_id=dados["usuario_id"],
            tipo_endereco=dados.get("tipo_endereco", "CASA"),
            cep=dados_cep["cep"],
            logradouro=logradouro,
            numero=numero,
            complemento=(dados.get("complemento") or "").strip() or None,
            bairro=bairro,
            cidade=cidade,
            uf=uf,
            latitude=lat,
            longitude=lng,
        )

        try:
            db.session.add(endereco)
            db.session.commit()
            return endereco, None, 201
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao persistir endereço: {str(exc)}", 500

    @staticmethod
    def buscar_por_id(id: int):
        """Busca um endereço específico pela chave primária."""
        endereco = db.session.get(Endereco, id)
        if not endereco:
            return None, "Endereço não encontrado", 404
        return endereco, None, 200

    @staticmethod
    def listar_por_usuario(usuario_id: int):
        """Lista todos os endereços vinculados a um usuário."""
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            return None, "Usuário informado não existe", 404

        enderecos = Endereco.query.filter_by(usuario_id=usuario_id).all()
        return enderecos, None, 200

    @staticmethod
    def atualizar(id: int, dados: dict):
        """
        Atualiza dados do endereço.
        Se o CEP mudar, revalida via ViaCEP e recalcula coordenadas.
        Se mudar número/rua, recalcula as coordenadas.
        """
        endereco = db.session.get(Endereco, id)
        if not endereco:
            return None, "Endereço não encontrado", 404

        if not dados:
            return None, "Dados não fornecidos", 400

        houve_mudanca_geografica = False

        novo_cep = dados.get("cep")
        if novo_cep and novo_cep.replace("-", "").strip() != endereco.cep.replace("-", "").strip():
            try:
                dados_cep = EnderecoService.consultar_viacep(novo_cep)
            except ValueError as err:
                return None, str(err), 400
            except RuntimeError as err:
                return None, str(err), 502

            endereco.cep = dados_cep["cep"]
            endereco.cidade = dados_cep["cidade"]
            endereco.uf = dados_cep["uf"]
            endereco.logradouro = (dados_cep.get("logradouro") or dados.get("logradouro") or endereco.logradouro).strip()
            endereco.bairro = (dados_cep.get("bairro") or dados.get("bairro") or "Centro").strip()
            houve_mudanca_geografica = True

        else:
            if dados.get("logradouro") and dados["logradouro"].strip() != endereco.logradouro:
                endereco.logradouro = dados["logradouro"].strip()
                houve_mudanca_geografica = True

            if dados.get("bairro"):
                endereco.bairro = dados["bairro"].strip()

        if dados.get("numero") and str(dados["numero"]).strip() != endereco.numero:
            endereco.numero = str(dados["numero"]).strip()
            houve_mudanca_geografica = True

        if "complemento" in dados:
            endereco.complemento = (dados.get("complemento") or "").strip() or None

        if dados.get("tipo_endereco"):
            endereco.tipo_endereco = dados["tipo_endereco"]

        if houve_mudanca_geografica:
            lat, lng = EnderecoService.obter_coordenadas(
                logradouro=endereco.logradouro,
                numero=endereco.numero,
                bairro=endereco.bairro,
                cidade=endereco.cidade,
                uf=endereco.uf,
                cep=endereco.cep        
            )
            endereco.latitude = lat
            endereco.longitude = lng

        try:
            db.session.commit()
            return endereco, None, 200
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar endereço: {str(exc)}", 500

    @staticmethod
    def deletar(id: int):
        """Remove um endereço pelo ID."""
        endereco = db.session.get(Endereco, id)
        if not endereco:
            return None, "Endereço não encontrado", 404

        try:
            db.session.delete(endereco)
            db.session.commit()
            return {"mensagem": f"Endereço {id} deletado com sucesso"}, None, 200
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao deletar endereço: {str(exc)}", 500