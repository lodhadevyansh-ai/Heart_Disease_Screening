"""add_user_id_to_patients

Revision ID: d8f14b2e8a91
Revises: c7e8291a02f3
Create Date: 2026-10-19 22:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8f14b2e8a91'
down_revision = 'c7e8291a02f3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_patients_user_id', 'users', ['user_id'], ['id'], ondelete='CASCADE')
        batch_op.create_index(batch_op.f('ix_patients_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_patients_user_id'))
        batch_op.drop_constraint('fk_patients_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
