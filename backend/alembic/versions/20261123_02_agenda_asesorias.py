"""Agenda por fecha y asesorías individuales/grupales con participantes."""

from alembic import op
import sqlalchemy as sa

revision = "20261123_02"
down_revision = "20261123_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "disponibilidades",
        sa.Column("id_disponibilidad", sa.Integer(), primary_key=True),
        sa.Column("id_docente", sa.BigInteger(), sa.ForeignKey("docentes.id_docente"), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modalidad", sa.String(15), nullable=False),
        sa.Column("ubicacion", sa.String(300), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("inicio < fin", name="ck_disponibilidad_intervalo"),
        sa.CheckConstraint("modalidad IN ('presencial','virtual')", name="ck_disponibilidad_modalidad"),
        sa.CheckConstraint("estado IN ('activa','cancelada')", name="ck_disponibilidad_estado"),
    )
    op.create_index("ix_disponibilidad_docente_inicio", "disponibilidades", ["id_docente", "inicio"])
    op.create_table(
        "asesorias",
        sa.Column("id_asesoria", sa.Integer(), primary_key=True),
        sa.Column("id_docente", sa.BigInteger(), sa.ForeignKey("docentes.id_docente"), nullable=False),
        sa.Column(
            "id_disponibilidad",
            sa.Integer(),
            sa.ForeignKey("disponibilidades.id_disponibilidad"),
            nullable=False,
        ),
        sa.Column("id_tema", sa.Integer(), sa.ForeignKey("temas.id_tema"), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tipo", sa.String(15), nullable=False),
        sa.Column("cupo_maximo", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("motivo_cancelacion", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("inicio < fin", name="ck_asesoria_intervalo"),
        sa.CheckConstraint("tipo IN ('individual','grupal')", name="ck_asesoria_tipo"),
        sa.CheckConstraint("estado IN ('programada','cancelada','finalizada')", name="ck_asesoria_estado"),
        sa.CheckConstraint(
            "(tipo = 'individual' AND cupo_maximo = 1) OR (tipo = 'grupal' AND cupo_maximo BETWEEN 2 AND 50)",
            name="ck_asesoria_cupo",
        ),
    )
    op.create_index("ix_asesoria_docente_inicio", "asesorias", ["id_docente", "inicio"])
    op.create_table(
        "participantes_asesoria",
        sa.Column("id_participante", sa.Integer(), primary_key=True),
        sa.Column("id_asesoria", sa.Integer(), sa.ForeignKey("asesorias.id_asesoria"), nullable=False),
        sa.Column(
            "id_estudiante", sa.BigInteger(), sa.ForeignKey("estudiantes.id_estudiante"), nullable=False
        ),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("id_asesoria", "id_estudiante", name="uq_participante_asesoria_estudiante"),
        sa.CheckConstraint(
            "estado IN ('reservada','cancelada','asistio','no_asistio')", name="ck_participante_estado"
        ),
    )
    op.create_index("ix_participante_estudiante", "participantes_asesoria", ["id_estudiante"])


def downgrade():
    op.drop_table("participantes_asesoria")
    op.drop_table("asesorias")
    op.drop_table("disponibilidades")
