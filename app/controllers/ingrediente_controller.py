from ..database import db
from ..models.models import Ingrediente


class IngredienteController:

    @staticmethod
    def autocomplete(termo_busca, limite=10):
        """Retorna sugestões de ingredientes já existentes no catálogo mestre."""
        if not termo_busca or not termo_busca.strip():
            return [], None, 200

        termo = f"%{termo_busca.strip()}%"
        ingredientes = (
            Ingrediente.query.filter(Ingrediente.nome.ilike(termo))
            .order_by(Ingrediente.nome.asc())
            .limit(limite)
            .all()
        )
        return ingredientes, None, 200