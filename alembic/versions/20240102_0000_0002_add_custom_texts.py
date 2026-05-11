"""Add customizable scene text fields to products table.

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("welcome_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("success_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("already_purchased_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("file_caption", sa.String(256), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("file_caption")
        batch_op.drop_column("already_purchased_text")
        batch_op.drop_column("success_text")
        batch_op.drop_column("welcome_text")
