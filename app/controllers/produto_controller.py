from sqlalchemy import and_
from ..database import db
from ..models.models import Produto, Restaurante


class ProdutoController:

    @staticmethod
    def criar(dados):
        """Valida e persiste um novo produto."""
        campos_obrigatorios = ["restaurante_id", "nome", "descricao", "preco"]
        for campo in campos_obrigatorios:
            if dados.get(campo) is None or dados.get(campo) == "":
                return None, f"Campo '{campo}' é obrigatório", 400

        try:
            preco = float(dados["preco"])
            if preco <= 0:
                return None, "O preço deve ser maior que zero", 400
        except (ValueError, TypeError):
            return None, "Campo 'preco' deve ser um número válido", 400

        restaurante = db.session.get(Restaurante, dados["restaurante_id"])
        if not restaurante:
            return None, "Restaurante não encontrado", 404

        produto = Produto(
            restaurante_id=dados["restaurante_id"],
            nome=dados["nome"].strip(),
            descricao=dados["descricao"].strip(),
            preco=preco,
            disponivel=dados.get("disponivel", True),
        )

        db.session.add(produto)
        db.session.commit()
        return produto, None, 201

    @staticmethod
    def buscar_por_id(id):
        """Busca um produto pelo ID."""
        produto = db.session.get(Produto, id)
        if not produto:
            return None, "Produto não encontrado", 404
        return produto, None, 200

    @staticmethod
    def buscar(filtros):
        """
        Busca e filtra produtos no catálogo exclusivamente pelo nome.
        filtros aceitos:
          - q: busca textual no nome do produto (case-insensitive)
          - restaurante_id: filtra produtos de uma loja específica
        """
        query = Produto.query.filter(Produto.disponivel.is_(True))

        if filtros.get("restaurante_id"):
            query = query.filter(Produto.restaurante_id == filtros["restaurante_id"])

        termo = filtros.get("q")
        if termo and termo.strip():
            palavras = [p.strip() for p in termo.strip().split() if p.strip()]

            if palavras:
                condicoes_nome = [Produto.nome.ilike(f"%{palavra}%") for palavra in palavras]
                query = query.filter(and_(*condicoes_nome))

        produtos = query.order_by(Produto.nome.asc()).all()
        return produtos, None, 200

    @staticmethod
    def atualizar(id, dados):
        """Atualiza dados cadastrais do produto."""
        produto = db.session.get(Produto, id)
        if not produto:
            return None, "Produto não encontrado", 404

        if not dados:
            return None, "Dados não fornecidos", 400

        if "nome" in dados:
            produto.nome = dados["nome"].strip()

        if "descricao" in dados:
            produto.descricao = dados["descricao"].strip()

        if "preco" in dados:
            try:
                preco = float(dados["preco"])
                if preco < 0:
                    return None, "O preço deve ser positivo", 400
                produto.preco = preco
            except (ValueError, TypeError):
                return None, "Campo 'preco' deve ser numérico", 400

        if "disponivel" in dados:
            produto.disponivel = bool(dados["disponivel"])

        db.session.commit()
        return produto, None, 200

    @staticmethod
    def deletar(id):
        """Remove o produto."""
        produto = db.session.get(Produto, id)
        if not produto:
            return None, "Produto não encontrado", 404

        db.session.delete(produto)
        db.session.commit()
        return {"mensagem": f"Produto {id} deletado com sucesso"}, None, 200

    @staticmethod
    def listar_por_restaurante(restaurante_id):
        """Lista todos os produtos cadastrados de um restaurante específico."""
        restaurante = db.session.get(Restaurante, restaurante_id)
        if not restaurante:
            return None, "Restaurante não encontrado", 404

        produtos = (
            Produto.query.filter_by(restaurante_id=restaurante_id)
            .order_by(Produto.nome.asc())
            .all()
        )
        return produtos, None, 200