"""Adicionando colunas asaas

Revision ID: 539e026e6ba9
Revises: df1c70580507
Create Date: 2026-10-11 20:33:11.861723

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '539e026e6ba9'
down_revision = 'df1c70580507'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    colunas_pedido = [c['name'] for c in inspector.get_columns('pedido')]

    with op.batch_alter_table('pedido', schema=None) as batch_op:
        if 'gateway_pagamento_id' not in colunas_pedido:
            batch_op.add_column(sa.Column('gateway_pagamento_id', sa.String(length=100), nullable=True))
            batch_op.create_index(batch_op.f('ix_pedido_gateway_pagamento_id'), ['gateway_pagamento_id'], unique=False)
        if 'url_pagamento' not in colunas_pedido:
            batch_op.add_column(sa.Column('url_pagamento', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('pedido', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pedido_gateway_pagamento_id'))
        batch_op.drop_column('url_pagamento')
        batch_op.drop_column('gateway_pagamento_id')
