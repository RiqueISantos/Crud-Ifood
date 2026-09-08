from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Float, Index, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class CodigoVerificacao(Base):
    __tablename__ = "codigos_verificacao"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    destino = Column(String(150), nullable=False, index=True)
    canal = Column(String(20), nullable=False)
    codigo = Column(String(6), nullable=False)
    expira_em = Column(Float, nullable=False)
    verificado = Column(Boolean, default=False, nullable=False)
    verificado_expira_em = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_destino_canal_verificado", "destino", "canal", "verificado"),
    )


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nome = Column(String(50), nullable=False)
    email = Column(String(254), unique=True, nullable=False, index=True)
    telefone = Column(String(20), nullable=True, index=True)
    documento = Column(String(20), nullable=True) 
    criado_em = Column(DateTime, server_default=func.now())


class Endereco(Base):
    __tablename__ = "enderecos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    tipo_endereco = Column(String(30), nullable=False, default="CASA")  # CASA, TRABALHO, RESTAURANTE

    logradouro = Column(String(100), nullable=False)
    numero = Column(String(10), nullable=False)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(50), nullable=False)
    cidade = Column(String(50), nullable=False)
    uf = Column(String(2), nullable=False)
    cep = Column(String(10), nullable=False)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    usuario_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=True, index=True)
    
    parceiro_id = Column(BigInteger, ForeignKey("usuarios.id"), nullable=True, index=True)