from typing import List, Optional
from sqlalchemy import String, Boolean, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Role(Base):
    """
    Catálogo de roles del sistema:
    estudiante, docente, administrador, etc.
    """
    __tablename__ = "roles"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relación 1:N -> un rol tiene muchos usuarios
    usuarios: Mapped[List["User"]] = relationship("User", back_populates="rol")


class User(Base):
    """
    Cuenta de acceso al sistema. Un usuario tiene UN rol.
    Sus datos académicos viven en `estudiantes` o `docentes` (perfiles).
    """
    __tablename__ = "usuarios"

    # BigInteger para coincidir con el tipo de las FK en profiles.py
    id_usuario: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_rol: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id_rol"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    # unique=True -> no se permiten dos cuentas con el mismo correo
    correo: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    # Aquí se guarda el HASH, nunca la contraseña en texto plano
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relaciones
    rol: Mapped["Role"] = relationship("Role", back_populates="usuarios")
    # Se dejan sin back_populates para no modificar profiles.py en este paso.
    estudiante: Mapped[Optional["Student"]] = relationship("Student")
    docente: Mapped[Optional["Teacher"]] = relationship("Teacher")
