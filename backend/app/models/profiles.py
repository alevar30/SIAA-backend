from typing import Optional
from sqlalchemy import String, SmallInteger, BigInteger, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Student(Base):
    __tablename__ = "estudiantes"

    id_estudiante: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id_usuario"), unique=True, nullable=False)
    id_carrera: Mapped[int] = mapped_column(Integer, ForeignKey("carreras.id_carrera"), nullable=False)
    matricula: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    semestre: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    usuario: Mapped["User"] = relationship("User")
    carrera: Mapped["Career"] = relationship("Career", back_populates="estudiantes")


class Teacher(Base):
    __tablename__ = "docentes"

    id_docente: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id_usuario"), unique=True, nullable=False)
    numero_empleado: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    departamento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    usuario: Mapped["User"] = relationship("User")