"""Versionar tokens para revocar sesiones al cambiar la contraseña.

Revision ID: 20261030_01
Revises: 6569fb796f37
"""
from alembic import op
import sqlalchemy as sa

revision = "20261030_01"
down_revision = "6569fb796f37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("token_version", sa.Integer(), server_default="1", nullable=False))
    op.create_index("uq_usuarios_correo_lower", "usuarios", [sa.text("lower(correo)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_usuarios_correo_lower", table_name="usuarios")
    op.drop_column("usuarios", "token_version")
