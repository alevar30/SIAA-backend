"""Agenda por fecha, sesiones y participación conservada para historial."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Availability(Base):
    __tablename__ = "disponibilidades"
    __table_args__ = (
        CheckConstraint("inicio < fin", name="ck_disponibilidad_intervalo"),
        CheckConstraint("modalidad IN ('presencial','virtual')", name="ck_disponibilidad_modalidad"),
        CheckConstraint("estado IN ('activa','cancelada')", name="ck_disponibilidad_estado"),
        Index("ix_disponibilidad_docente_inicio", "id_docente", "inicio"),
    )
    id_disponibilidad: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_docente: Mapped[int] = mapped_column(BigInteger, ForeignKey("docentes.id_docente"))
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    modalidad: Mapped[str] = mapped_column(String(15))
    ubicacion: Mapped[str] = mapped_column(String(300))
    estado: Mapped[str] = mapped_column(String(15), default="activa")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class AdvisingSession(Base):
    __tablename__ = "asesorias"
    __table_args__ = (
        CheckConstraint("inicio < fin", name="ck_asesoria_intervalo"),
        CheckConstraint("tipo IN ('individual','grupal')", name="ck_asesoria_tipo"),
        CheckConstraint("estado IN ('programada','cancelada','finalizada')", name="ck_asesoria_estado"),
        CheckConstraint(
            "(tipo = 'individual' AND cupo_maximo = 1) OR (tipo = 'grupal' AND cupo_maximo BETWEEN 2 AND 50)",
            name="ck_asesoria_cupo",
        ),
        Index("ix_asesoria_docente_inicio", "id_docente", "inicio"),
    )
    id_asesoria: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_docente: Mapped[int] = mapped_column(BigInteger, ForeignKey("docentes.id_docente"))
    id_disponibilidad: Mapped[int] = mapped_column(ForeignKey("disponibilidades.id_disponibilidad"))
    id_tema: Mapped[int] = mapped_column(ForeignKey("temas.id_tema"))
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tipo: Mapped[str] = mapped_column(String(15))
    cupo_maximo: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(15), default="programada")
    motivo_cancelacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class Participant(Base):
    __tablename__ = "participantes_asesoria"
    __table_args__ = (
        UniqueConstraint("id_asesoria", "id_estudiante", name="uq_participante_asesoria_estudiante"),
        CheckConstraint(
            "estado IN ('reservada','cancelada','asistio','no_asistio')", name="ck_participante_estado"
        ),
        Index("ix_participante_estudiante", "id_estudiante"),
    )
    id_participante: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_asesoria: Mapped[int] = mapped_column(ForeignKey("asesorias.id_asesoria"))
    id_estudiante: Mapped[int] = mapped_column(BigInteger, ForeignKey("estudiantes.id_estudiante"))
    estado: Mapped[str] = mapped_column(String(15), default="reservada")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
