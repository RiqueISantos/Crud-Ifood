import enum
from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Float, Index, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class StatusPedido(enum.Enum):
    AGUARDANDO_PAGAMENTO   = "AGUARDANDO_PAGAMENTO"    
    AGUARDANDO_CONFIRMACAO = "AGUARDANDO_CONFIRMACAO"  
    CONFIRMADO             = "CONFIRMADO"              
    EM_PREPARACAO          = "EM_PREPARACAO"           
    SAIU_PARA_ENTREGA      = "SAIU_PARA_ENTREGA"       
    ENTREGUE               = "ENTREGUE"                
    CANCELADO              = "CANCELADO"               


class FormaPagamento(enum.Enum):
    CREDITO   = "CREDITO"
    DEBITO    = "DEBITO"
    PIX       = "PIX"
    DINHEIRO  = "DINHEIRO"
    VALE      = "VALE"


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
    asaas_customer_id = db.Column(db.String(50), nullable=True)


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


class Sacola(Base):
    __tablename__ = "sacola"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id = Column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    restaurante_id = Column(
        BigInteger,
        ForeignKey("restaurante.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criado_em = Column(DateTime, server_default=func.now(), nullable=False)

    usuario = relationship("Usuario", backref="sacola")
    restaurante = relationship("Restaurante")
    itens = relationship(
        "ItemSacola",
        back_populates="sacola",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ItemSacola(Base):
    __tablename__ = "item_sacola"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sacola_id = Column(
        BigInteger,
        ForeignKey("sacola.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    produto_id = Column(
        BigInteger,
        ForeignKey("produto.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantidade = Column(BigInteger, default=1, nullable=False)
    observacao = Column(String(255), nullable=True)

    sacola = relationship("Sacola", back_populates="itens")
    produto = relationship("Produto", lazy="selectin")




    


class Pedido(Base):
    __tablename__ = "pedido"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    usuario_id = Column(
        BigInteger,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    restaurante_id = Column(
        BigInteger,
        ForeignKey("restaurante.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    endereco_id = Column(
        BigInteger,
        ForeignKey("enderecos.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        Enum(StatusPedido),
        nullable=False,
        default=StatusPedido.AGUARDANDO_CONFIRMACAO,
        index=True,
    )
    forma_pagamento = Column(Enum(FormaPagamento), nullable=True)

    subtotal      = Column(Float, nullable=False, default=0.0)
    taxa_entrega  = Column(Float, nullable=False, default=0.0)
    total         = Column(Float, nullable=False, default=0.0)

    observacao = Column(String(500), nullable=True)
    
    gateway_pagamento_id = Column(String(100), nullable=True, index=True) 
    url_pagamento = Column(String(500), nullable=True)

    criado_em     = Column(DateTime, server_default=func.now(), nullable=False)
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    usuario    = relationship("Usuario")
    restaurante = relationship("Restaurante")
    endereco   = relationship("Endereco")
    itens      = relationship(
        "ItemPedido",
        back_populates="pedido",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ItemPedido(Base):
    __tablename__ = "item_pedido"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    pedido_id = Column(
        BigInteger,
        ForeignKey("pedido.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    produto_id = Column(
        BigInteger,
        ForeignKey("produto.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Cópia imutável no momento do pedido — protege histórico se o produto mudar
    nome_produto    = Column(String(60),  nullable=False)
    preco_unitario  = Column(Float,       nullable=False)
    quantidade      = Column(BigInteger,  nullable=False, default=1)
    observacao      = Column(String(255), nullable=True)
    subtotal_item   = Column(Float,       nullable=False)

    pedido  = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto")
