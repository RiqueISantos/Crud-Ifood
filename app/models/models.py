from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Float, Index, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
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
    



class Restaurante(Base):
    __tablename__ = 'restaurante'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nome = Column(String(50), nullable=False)
    email = Column(String(254), unique=True, nullable=False, index=True)
    telefone = Column(String(20), nullable=False, index=True)
    categoria_principal = Column(String(50), nullable=False)
    taxa_entrega = Column(Float, nullable=True)
    tempo_estimado = Column(String(20), nullable=True)
    logradouro = Column(String(254), nullable=False)
    numero = Column(String(10), nullable=False)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(50), nullable=False)
    cidade = Column(String(50), nullable=False)
    uf = Column(String(2), nullable=False)
    cep = Column(String(10), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())

    produtos = relationship("Produto", back_populates="restaurante", cascade="all, delete-orphan")

#Tabela associativa (produto_ingrediente)
produto_ingrediente = Table(
    "produto_ingrediente",
    Base.metadata,
    Column(
        "produto_id",
        BigInteger,
        ForeignKey("produto.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "ingrediente_id",
        BigInteger,
        ForeignKey("ingrediente.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)

class Ingrediente(Base):
    __tablename__ = "ingrediente"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nome = Column(String(60), nullable=False, unique=True, index=True)

    produtos = relationship(
        "Produto",
        secondary=produto_ingrediente,
        back_populates="ingredientes",
    )

class Produto(Base):
    __tablename__ = "produto"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    restaurante_id = Column(
        BigInteger,
        ForeignKey("restaurante.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome = Column(String(60), nullable=False, index=True)
    descricao = Column(String(8000), nullable=False)
    preco = Column(Float, nullable=False)
    disponivel = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, server_default=func.now())

    restaurante = relationship("Restaurante", back_populates="produtos")

    ingredientes = relationship(
        "Ingrediente",
        secondary=produto_ingrediente,
        back_populates="produtos",
        lazy="selectin",
    )