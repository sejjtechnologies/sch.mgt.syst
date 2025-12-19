"""empty message

Revision ID: 5ce307963cba
Revises: fea72f024367, add_stream_id_to_fee_structures
Create Date: 2025-12-19 11:28:16.919213

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5ce307963cba'
down_revision = ('fea72f024367', 'add_stream_id_to_fee_structures')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
