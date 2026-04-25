"""feat: dodanie max_volume_m3 oraz relacji User-Warehouse dla VROOM

Revision ID: afa4756e1e59
Revises: 72fab87dd5d8
Create Date: 2026-04-25 15:44:05.633748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'afa4756e1e59'
down_revision: Union[str, Sequence[str], None] = '72fab87dd5d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # RĘCZNIE POPRAWIONE KOMENDY ALEMBICA
    op.add_column('dimensional_tariffs', sa.Column('max_volume_m3', sa.Float(), server_default='0.1', nullable=False))
    op.add_column('users', sa.Column('warehouse_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'users', 'warehouses', ['warehouse_id'], ['warehouse_id'])
    op.add_column('vehicles', sa.Column('capacity_m3', sa.Float(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # RĘCZNIE POPRAWIONE KOMENDY ALEMBICA
    op.drop_column('vehicles', 'capacity_m3')
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'warehouse_id')
    op.drop_column('dimensional_tariffs', 'max_volume_m3')
    # ### end Alembic commands ###
