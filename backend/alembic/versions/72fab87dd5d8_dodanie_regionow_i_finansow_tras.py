"""dodanie_regionow_i_finansow_tras

Revision ID: 72fab87dd5d8
Revises: c226b2f3426a
Create Date: 2026-04-22 11:07:04.733087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72fab87dd5d8'
down_revision: Union[str, Sequence[str], None] = 'c226b2f3426a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================
    # 1. TWORZENIE TABELI: regions
    # ==========================================
    op.create_table(
        'regions',
        sa.Column('region_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('region_name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('region_id')
    )

    # ==========================================
    # 2. AKTUALIZACJA TABELI: routes (Finanse i dystans)
    # ==========================================
    op.add_column('routes', sa.Column('total_distance_km', sa.Float(), nullable=True))
    op.add_column('routes', sa.Column('total_revenue', sa.Float(), nullable=True))
    op.add_column('routes', sa.Column('route_cost', sa.Float(), nullable=True))

    # ==========================================
    # 3. AKTUALIZACJA TABELI: parcels (Przypisanie do regionu)
    # ==========================================
    op.add_column('parcels', sa.Column('target_region_id', sa.Integer(), nullable=True))
    
    # Tworzymy klucz obcy (Foreign Key) łączący paczkę z regionem
    op.create_foreign_key(
        constraint_name='fk_parcels_target_region_id_regions',
        source_table='parcels',
        referent_table='regions',
        local_cols=['target_region_id'],
        remote_cols=['region_id']
    )


def downgrade() -> None:
    # ==========================================
    # COFANIE ZMIAN (Wykonywane w odwrotnej kolejności!)
    # ==========================================
    
    # 1. Cofanie zmian w 'parcels'
    op.drop_constraint('fk_parcels_target_region_id_regions', 'parcels', type_='foreignkey')
    op.drop_column('parcels', 'target_region_id')

    # 2. Cofanie zmian w 'routes'
    op.drop_column('routes', 'route_cost')
    op.drop_column('routes', 'total_revenue')
    op.drop_column('routes', 'total_distance_km')

    # 3. Usunięcie tabeli 'regions'
    op.drop_table('regions')