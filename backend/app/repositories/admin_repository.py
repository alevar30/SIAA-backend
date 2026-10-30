from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role
from app.models.profiles import Student, Teacher


class AdminRepository:
    @staticmethod
    async def get_role_by_name(db: AsyncSession, nombre: str) -> Optional[Role]:
        result = await db.execute(select(Role).where(Role.nombre == nombre))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_correo(db: AsyncSession, correo: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.correo == correo))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_student_by_matricula(db: AsyncSession, matricula: str) -> Optional[Student]:
        result = await db.execute(select(Student).where(Student.matricula == matricula))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_teacher_by_numero_empleado(db: AsyncSession, numero_empleado: str) -> Optional[Teacher]:
        result = await db.execute(select(Teacher).where(Teacher.numero_empleado == numero_empleado))
        return result.scalar_one_or_none()
