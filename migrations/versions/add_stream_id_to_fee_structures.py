"""add stream_id to fee_structures

Revision ID: add_stream_id_to_fee_structures
Revises: bursa20251216
Create Date: 2025-12-16 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_stream_id_to_fee_structures'
down_revision = 'bursa20251216'
branch_labels = None
depends_on = None


def upgrade():
    # Add stream_id column to fee_structures table
    op.add_column('fee_structures', sa.Column('stream_id', sa.String(length=36), nullable=True))


def downgrade():
    # Remove stream_id column from fee_structures table
    op.drop_column('fee_structures', 'stream_id')