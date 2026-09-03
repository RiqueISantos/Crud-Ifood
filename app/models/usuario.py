from ..database import db
from datetime import datetime


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    telefone = db.Column(db.String(20), unique=False, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
