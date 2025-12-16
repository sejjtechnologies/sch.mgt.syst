"""add grade columns to pupil_marks

Revision ID: 4d48d97eb80d
Revises: 8ab4e2f861bd
Create Date: 2025-12-16 10:46:59.071053

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d48d97eb80d'
down_revision = '8ab4e2f861bd'
branch_labels = None
depends_on = None


def upgrade():
    # Add grade columns to pupil_marks table
    op.add_column('pupil_marks', sa.Column('english_grade', sa.String(5), nullable=True))
    op.add_column('pupil_marks', sa.Column('mathematics_grade', sa.String(5), nullable=True))
    op.add_column('pupil_marks', sa.Column('science_grade', sa.String(5), nullable=True))
    op.add_column('pupil_marks', sa.Column('social_studies_grade', sa.String(5), nullable=True))
    op.add_column('pupil_marks', sa.Column('overall_grade', sa.String(5), nullable=True))


def downgrade():
    # Remove grade columns from pupil_marks table
    op.drop_column('pupil_marks', 'english_grade')
    op.drop_column('pupil_marks', 'mathematics_grade')
    op.drop_column('pupil_marks', 'science_grade')
    op.drop_column('pupil_marks', 'social_studies_grade')
    op.drop_column('pupil_marks', 'overall_grade')
