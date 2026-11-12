"""Permite dar de alta estudiantes antes de completar su perfil."""

import sqlalchemy as sa
from alembic import op

revision = "20261111_01"
down_revision = "20261030_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("usuarios", sa.Column("apellidos", sa.String(150), nullable=True))
    op.alter_column("usuarios", "nombre", existing_type=sa.String(150), nullable=True)
    op.alter_column("usuarios", "correo", existing_type=sa.String(150), nullable=True)
    op.alter_column("estudiantes", "id_carrera", existing_type=sa.Integer(), nullable=True)


def downgrade():
    op.alter_column("estudiantes", "id_carrera", existing_type=sa.Integer(), nullable=False)
    op.alter_column("usuarios", "correo", existing_type=sa.String(150), nullable=False)
    op.alter_column("usuarios", "nombre", existing_type=sa.String(150), nullable=False)
    op.drop_column("usuarios", "apellidos")
