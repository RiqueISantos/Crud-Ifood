"""adiciona Pedido e ItemPedido com status e forma de pagamento

Revision ID: df1c70580507
Revises: 7b57e6fcf566
Create Date: 2026-10-04 18:33:05.103012

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'df1c70580507'
down_revision = '7b57e6fcf566'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tabelas = inspector.get_table_names()

    # Cria enums no Postgres se não existirem
    bind.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'statuspedido') THEN
                CREATE TYPE statuspedido AS ENUM (
                    'AGUARDANDO_PAGAMENTO', 'AGUARDANDO_CONFIRMACAO', 'CONFIRMADO',
                    'EM_PREPARACAO', 'SAIU_PARA_ENTREGA', 'ENTREGUE', 'CANCELADO'
                );
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'formapagamento') THEN
                CREATE TYPE formapagamento AS ENUM (
                    'CREDITO', 'DEBITO', 'PIX', 'DINHEIRO', 'VALE'
                );
            END IF;
        END $$;
    """))

    # Usa os enums já existentes sem tentar recriá-los (create_type=False)
    status_enum  = postgresql.ENUM(name='statuspedido',  create_type=False)
    pgto_enum    = postgresql.ENUM(name='formapagamento', create_type=False)

    # Cria tabela pedido se não existir
    if 'pedido' not in tabelas:
        op.create_table(
            'pedido',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('usuario_id', sa.BigInteger(), nullable=True),
            sa.Column('restaurante_id', sa.BigInteger(), nullable=True),
            sa.Column('endereco_id', sa.BigInteger(), nullable=True),
            sa.Column('status', status_enum, nullable=False),
            sa.Column('forma_pagamento', pgto_enum, nullable=True),
            sa.Column('subtotal', sa.Float(), nullable=False),
            sa.Column('taxa_entrega', sa.Float(), nullable=False),
            sa.Column('total', sa.Float(), nullable=False),
            sa.Column('observacao', sa.String(length=500), nullable=True),
            sa.Column('criado_em', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['endereco_id'], ['enderecos.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['restaurante_id'], ['restaurante.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('pedido', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_pedido_restaurante_id'), ['restaurante_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_pedido_status'), ['status'], unique=False)
            batch_op.create_index(batch_op.f('ix_pedido_usuario_id'), ['usuario_id'], unique=False)

    # Cria tabela item_pedido se não existir
    if 'item_pedido' not in tabelas:
        op.create_table(
            'item_pedido',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('pedido_id', sa.BigInteger(), nullable=False),
            sa.Column('produto_id', sa.BigInteger(), nullable=True),
            sa.Column('nome_produto', sa.String(length=60), nullable=False),
            sa.Column('preco_unitario', sa.Float(), nullable=False),
            sa.Column('quantidade', sa.BigInteger(), nullable=False),
            sa.Column('observacao', sa.String(length=255), nullable=True),
            sa.Column('subtotal_item', sa.Float(), nullable=False),
            sa.ForeignKeyConstraint(['pedido_id'], ['pedido.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['produto_id'], ['produto.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('item_pedido', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_item_pedido_pedido_id'), ['pedido_id'], unique=False)

    # Dropa tabelas legadas apenas se existirem
    if 'produto_ingrediente' in tabelas:
        op.drop_table('produto_ingrediente')
    if 'ingrediente' in tabelas:
        with op.batch_alter_table('ingrediente', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_ingrediente_nome'))
        op.drop_table('ingrediente')

    # Adiciona coluna asaas_customer_id em usuarios se não existir
    colunas_usuario = [c['name'] for c in inspector.get_columns('usuarios')]
    if 'asaas_customer_id' not in colunas_usuario:
        with op.batch_alter_table('usuarios', schema=None) as batch_op:
            batch_op.add_column(sa.Column('asaas_customer_id', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_column('asaas_customer_id')

    with op.batch_alter_table('item_pedido', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_item_pedido_pedido_id'))
    op.drop_table('item_pedido')

    with op.batch_alter_table('pedido', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pedido_usuario_id'))
        batch_op.drop_index(batch_op.f('ix_pedido_status'))
        batch_op.drop_index(batch_op.f('ix_pedido_restaurante_id'))
    op.drop_table('pedido')
