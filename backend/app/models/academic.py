from typing import Optional, List
from sqlalchemy import String, Boolean, SmallInteger, Integer, BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Career(Base):
    __tablename__ = "carreras"

    id_carrera: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    clave: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    estudiantes: Mapped[List["Student"]] = relationship("Student", back_populates="carrera")


class Subject(Base):
    __tablename__ = "materias"

    id_materia: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clave: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    temas: Mapped[List["Topic"]] = relationship("Topic", back_populates="materia")


class Topic(Base):
    __tablename__ = "temas"

    id_tema: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_materia: Mapped[int] = mapped_column(Integer, ForeignKey("materias.id_materia"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    materia: Mapped["Subject"] = relationship("Subject", back_populates="temas")