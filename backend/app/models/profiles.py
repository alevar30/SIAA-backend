from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, SmallInteger, BigInteger, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.academic import Career


class Student(Base):
    __tablename__ = "estudiantes"

    id_estudiante: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario"), unique=True, nullable=False
    )
    id_carrera: Mapped[int | None] = mapped_column(Integer, ForeignKey("carreras.id_carrera"), nullable=True)
    matricula: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    semestre: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    usuario: Mapped["User"] = relationship("User", back_populates="estudiante")
    carrera: Mapped[Optional["Career"]] = relationship("Career", back_populates="estudiantes")


class Teacher(Base):
    __tablename__ = "docentes"

    id_docente: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id_usuario"), unique=True, nullable=False
    )
    academic_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    numero_empleado: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    departamento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    usuario: Mapped["User"] = relationship("User", back_populates="docente")
