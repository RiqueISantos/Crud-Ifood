from sqlalchemy import not_, select
from ..database import db
from ..models.models import Produto, Ingrediente, Restaurante, produto_ingrediente



class ProdutoController:

    @staticmethod
    def _processar_ingredientes(nomes_ingredientes):
        """Busca ingredientes existentes no catálogo ou cria novos se não existirem."""
        ingredientes_obj = []
        for nome_cru in nomes_ingredientes:
            if not isinstance(nome_cru, str):
                continue
            nome_formatado = nome_cru.strip().title()
            if not nome_formatado:
                continue

            ingrediente = Ingrediente.query.filter_by(nome=nome_formatado).first()
            if not ingrediente:
                ingrediente = Ingrediente(nome=nome_formatado)
                db.session.add(ingrediente)
                db.session.flush() 

            ingredientes_obj.append(ingrediente)
        return ingredientes_obj

    @staticmethod
    def criar(dados):
        """Valida e persiste um novo produto com seus ingredientes."""
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

        lista_nomes = dados.get("ingredientes") or []
        ingredientes_associados = ProdutoController._processar_ingredientes(lista_nomes)

        produto = Produto(
            restaurante_id=dados["restaurante_id"],
            nome=dados["nome"].strip(),
            descricao=dados["descricao"].strip(),
            preco=preco,
            disponivel=dados.get("disponivel", True),
            ingredientes=ingredientes_associados,
        )

        db.session.add(produto)
        db.session.commit()
        return produto, None, 201

    @staticmethod
    def buscar_por_id(id):
        """Busca um produto pelo id."""
        produto = db.session.get(Produto, id)
        if not produto:
            return None, "Produto não encontrado", 404
        return produto, None, 200

    @staticmethod
    def buscar(filtros):
        """
        Busca e filtra produtos no catálogo.
        filtros aceitos:
          - q: busca no nome do produto ou nome do ingrediente
          - restaurante_id: filtra por restaurante
          - exclude: ingredientes para excluir separados por vírgula (ex: 'cebola,alho')
        """
        from sqlalchemy import or_, not_

        query = Produto.query.filter(Produto.disponivel.is_(True))

        if filtros.get("restaurante_id"):
            query = query.filter(Produto.restaurante_id == filtros["restaurante_id"])

        exclude_param = filtros.get("exclude")
        if exclude_param:
            termos_excluir = [item.strip() for item in exclude_param.split(",") if item.strip()]
            if termos_excluir:
                condicoes_exclusao = [
                    Ingrediente.nome.ilike(f"%{termo}%") for termo in termos_excluir
                ]
                
                produtos_indesejados = (
                    db.session.query(produto_ingrediente.c.produto_id)
                    .join(Ingrediente, produto_ingrediente.c.ingrediente_id == Ingrediente.id)
                    .filter(or_(*condicoes_exclusao))
                    .subquery()
                )

                query = query.filter(not_(Produto.id.in_(produtos_indesejados)))

        termo = filtros.get("q")
        if termo and termo.strip():
            palavras = [p.strip() for p in termo.strip().split() if p.strip()]

            if palavras:
                from sqlalchemy import and_, or_

                condicoes_palavras = []
                for palavra in palavras:
                    p_like = f"%{palavra}%"
                    condicoes_palavras.append(
                        or_(
                            Produto.nome.ilike(p_like),
                            Ingrediente.nome.ilike(p_like)
                        )
                    )

                query = query.join(Produto.ingredientes).filter(and_(*condicoes_palavras))

        produtos = query.distinct().all()
        return produtos, None, 200
    @staticmethod
    def atualizar(id, dados):
        """Atualiza dados do produto e opcionalmente recalcula os ingredientes."""
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

        if "ingredientes" in dados:
            produto.ingredientes = ProdutoController._processar_ingredientes(dados["ingredientes"])

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