"""Initial migration

Revision ID: 1d4a2717054a
Revises: cfe2217d4ddf
Create Date: 2024-06-17 21:23:19.802941

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1d4a2717054a'
down_revision = 'cfe2217d4ddf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('pdf_data', schema=None) as batch_op:
        batch_op.drop_column('energia_contratada2')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('pdf_data', schema=None) as batch_op:
        batch_op.add_column(sa.Column('energia_contratada2', sa.VARCHAR(length=100), nullable=True))

    # ### end Alembic commands ###
