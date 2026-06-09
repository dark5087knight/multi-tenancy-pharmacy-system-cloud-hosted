"""add is_pinned to medicine

Revision ID: 002_add_is_pinned_to_medicine
Revises: 001_initial_schema
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision = '002_add_is_pinned_to_medicine'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspect_obj = reflection.Inspector.from_engine(conn)
    columns = [c['name'] for c in inspect_obj.get_columns('medicines')]
    if 'is_pinned' not in columns:
        op.add_column('medicines', sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.text('false')))

def downgrade() -> None:
    conn = op.get_bind()
    inspect_obj = reflection.Inspector.from_engine(conn)
    columns = [c['name'] for c in inspect_obj.get_columns('medicines')]
    if 'is_pinned' in columns:
        op.drop_column('medicines', 'is_pinned')
