"""add i18n: user.language + product EN fields

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users.language
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("language", sa.String(length=2), nullable=False, server_default="ru")
        )

    # products — EN fields
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("name_en", sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column("description_en", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("welcome_text_en", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("success_text_en", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("already_purchased_text_en", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("file_caption_en", sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column("confirm_footer_text_en", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("buy_button_text_en", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("confirm_button_text_en", sa.String(length=128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("confirm_button_text_en")
        batch_op.drop_column("buy_button_text_en")
        batch_op.drop_column("confirm_footer_text_en")
        batch_op.drop_column("file_caption_en")
        batch_op.drop_column("already_purchased_text_en")
        batch_op.drop_column("success_text_en")
        batch_op.drop_column("welcome_text_en")
        batch_op.drop_column("description_en")
        batch_op.drop_column("name_en")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("language")
