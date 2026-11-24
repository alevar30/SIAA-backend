"""Conservar autor de temas nuevos sin atribuir los registros anteriores."""

from alembic import op
import sqlalchemy as sa

revision = "20261123_03"
down_revision = "20261123_02"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("temas", sa.Column("id_creador", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_tema_creador", "temas", "usuarios", ["id_creador"], ["id_usuario"])


def downgrade():
    op.drop_constraint("fk_tema_creador", "temas", type_="foreignkey")
    op.drop_column("temas", "id_creador")
