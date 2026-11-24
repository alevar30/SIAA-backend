"""Catálogo académico y asignaciones docentes con integridad relacional."""

from alembic import op
import sqlalchemy as sa

revision = "20261123_01"
down_revision = "20261111_01"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("carreras", "materias", "temas"):
        op.add_column(table, sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("docentes", sa.Column("academic_version", sa.Integer(), nullable=False, server_default="1"))
    op.create_unique_constraint("uq_tema_materia", "temas", ["id_tema", "id_materia"])
    op.create_table(
        "carrera_materia",
        sa.Column("id_carrera", sa.Integer(), sa.ForeignKey("carreras.id_carrera"), primary_key=True),
        sa.Column("id_materia", sa.Integer(), sa.ForeignKey("materias.id_materia"), primary_key=True),
    )
    op.create_table(
        "docente_materia",
        sa.Column("id_docente", sa.BigInteger(), sa.ForeignKey("docentes.id_docente"), primary_key=True),
        sa.Column("id_materia", sa.Integer(), sa.ForeignKey("materias.id_materia"), primary_key=True),
    )
    op.create_table(
        "docente_tema",
        sa.Column("id_docente", sa.BigInteger(), primary_key=True),
        sa.Column("id_tema", sa.Integer(), primary_key=True),
        sa.Column("id_materia", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_docente", "id_materia"],
            ["docente_materia.id_docente", "docente_materia.id_materia"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["id_tema", "id_materia"], ["temas.id_tema", "temas.id_materia"]),
    )


def downgrade():
    op.drop_table("docente_tema")
    op.drop_table("docente_materia")
    op.drop_table("carrera_materia")
    op.drop_constraint("uq_tema_materia", "temas", type_="unique")
    op.drop_column("docentes", "academic_version")
    for table in ("temas", "materias", "carreras"):
        op.drop_column(table, "version")
