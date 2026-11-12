from typing import TYPE_CHECKING, List, Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, BigInteger, ForeignKey, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.profiles import Student, Teacher


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
    nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    apellidos: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # unique=True -> no se permiten dos cuentas con el mismo correo
    correo: Mapped[str | None] = mapped_column(String(150), unique=True, nullable=True, index=True)
    __table_args__ = (Index("uq_usuarios_correo_lower", func.lower(correo), unique=True),)
    # Aquí se guarda el HASH, nunca la contraseña en texto plano
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Al crear con contraseña temporal aleatoria, se obliga al primer cambio
    debe_cambiar_contrasena: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False
    )
    fecha_ultimo_cambio: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    token_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    # Relaciones
    rol: Mapped["Role"] = relationship("Role", back_populates="usuarios")
    estudiante: Mapped[Optional["Student"]] = relationship("Student", back_populates="usuario", uselist=False)
    docente: Mapped[Optional["Teacher"]] = relationship("Teacher", back_populates="usuario", uselist=False)

    @property
    def nombre_completo(self) -> str:
        return " ".join(filter(None, (self.nombre, self.apellidos))) or "Perfil pendiente"

    @property
    def requiere_completar_perfil(self) -> bool:
        return self.estudiante is not None and self.estudiante.id_carrera is None
