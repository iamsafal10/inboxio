"""Add provider columns

Revision ID: 589a812cf888
Revises: 10877e2cf996
Create Date: 2026-08-23 07:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '589a812cf888'
down_revision: Union[str, None] = '10877e2cf996'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add provider column to eval_results
    op.add_column('eval_results', sa.Column('provider', sa.String(length=50), nullable=True))
    
    # Add provider column to memory_facts
    op.add_column('memory_facts', sa.Column('provider', sa.String(length=50), nullable=True))
    
    # Add provider column to profiles
    op.add_column('profiles', sa.Column('provider', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('profiles', 'provider')
    op.drop_column('memory_facts', 'provider')
    op.drop_column('eval_results', 'provider')
