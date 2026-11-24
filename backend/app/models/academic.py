from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import (
    String,
    Boolean,
    Integer,
    ForeignKey,
    Text,
    UniqueConstraint,
    BigInteger,
    ForeignKeyConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.profiles import Student


class Career(Base):
    __tablename__ = "carreras"

    id_carrera: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    clave: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    estudiantes: Mapped[List["Student"]] = relationship("Student", back_populates="carrera")


class Subject(Base):
    __tablename__ = "materias"

    id_materia: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clave: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    temas: Mapped[List["Topic"]] = relationship("Topic", back_populates="materia")


class Topic(Base):
    __tablename__ = "temas"
    __table_args__ = (UniqueConstraint("id_tema", "id_materia", name="uq_tema_materia"),)

    id_tema: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_materia: Mapped[int] = mapped_column(Integer, ForeignKey("materias.id_materia"), nullable=False)
    id_creador: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    materia: Mapped["Subject"] = relationship("Subject", back_populates="temas")


class CareerSubject(Base):
    __tablename__ = "carrera_materia"
    id_carrera: Mapped[int] = mapped_column(ForeignKey("carreras.id_carrera"), primary_key=True)
    id_materia: Mapped[int] = mapped_column(ForeignKey("materias.id_materia"), primary_key=True)


class TeacherSubject(Base):
    __tablename__ = "docente_materia"
    id_docente: Mapped[int] = mapped_column(BigInteger, ForeignKey("docentes.id_docente"), primary_key=True)
    id_materia: Mapped[int] = mapped_column(ForeignKey("materias.id_materia"), primary_key=True)


class TeacherTopic(Base):
    __tablename__ = "docente_tema"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_docente", "id_materia"],
            ["docente_materia.id_docente", "docente_materia.id_materia"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["id_tema", "id_materia"], ["temas.id_tema", "temas.id_materia"]),
    )
    id_docente: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_tema: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_materia: Mapped[int] = mapped_column(Integer, nullable=False)
