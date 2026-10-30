from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.user import User
from app.models.profiles import Student, Teacher


class AuthRepository:
    @staticmethod
    async def get_by_correo(db: AsyncSession, correo: str) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(joinedload(User.rol), joinedload(User.estudiante), joinedload(User.docente))
            .where(User.correo == correo)
        )
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def get_by_matricula(db: AsyncSession, matricula: str) -> Optional[User]:
        result = await db.execute(
            select(User)
            .join(Student, Student.id_usuario == User.id_usuario)
            .options(joinedload(User.rol), joinedload(User.estudiante), joinedload(User.docente))
            .where(Student.matricula == matricula)
        )
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def get_by_numero_empleado(db: AsyncSession, numero_empleado: str) -> Optional[User]:
        result = await db.execute(
            select(User)
            .join(Teacher, Teacher.id_usuario == User.id_usuario)
            .options(joinedload(User.rol), joinedload(User.estudiante), joinedload(User.docente))
            .where(Teacher.numero_empleado == numero_empleado)
        )
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, id_usuario: int) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(joinedload(User.rol), joinedload(User.estudiante), joinedload(User.docente))
            .where(User.id_usuario == id_usuario)
        )
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def update_password(db: AsyncSession, usuario: User, new_password_hash: str) -> User:
        usuario.password_hash = new_password_hash
        usuario.debe_cambiar_contrasena = False
        usuario.fecha_ultimo_cambio = datetime.utcnow()
        await db.commit()
        await db.refresh(usuario)
        return usuario
