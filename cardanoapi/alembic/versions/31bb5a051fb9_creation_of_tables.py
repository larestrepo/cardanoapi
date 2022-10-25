"""Creation of tables

Revision ID: 31bb5a051fb9
Revises: 
Create Date: 2022-10-24 19:23:47.377676

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '31bb5a051fb9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('wallet',
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('base_addr', sa.Text(), nullable=False),
    sa.Column('payment_addr', sa.Text(), nullable=False),
    sa.Column('payment_skey', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('payment_vkey', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('stake_addr', sa.Text(), nullable=False),
    sa.Column('stake_skey', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('stake_vkey', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('hash_verification_key', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wallet_id'), 'wallet', ['id'], unique=False)
    op.create_table('users',
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('id_wallet', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('username', sa.String(length=100), nullable=False),
    # sa.Column('role', sa.Enum('admin', 'user', 'investor', name='role'), nullable=True),
    sa.Column('is_verified', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['id_wallet'], ['wallet.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column(
        'users',
        sa.Column('role', sa.Enum('admin', 'user', 'investor', name='role'), nullable=True),
    )

    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_wallet_id'), table_name='wallet')
    op.drop_table('wallet')
    # ### end Alembic commands ###