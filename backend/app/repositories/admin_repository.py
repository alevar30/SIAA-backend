from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.academic import Career
from app.models.user import User, Role
from app.models.profiles import Student, Teacher


class AdminRepository:
    @staticmethod
    async def get_role_by_name(db: AsyncSession, nombre: str) -> Role | None:
        return await db.scalar(select(Role).where(Role.nombre == nombre))

    @staticmethod
    async def get_user_by_correo(db: AsyncSession, correo: str) -> User | None:
        return await db.scalar(select(User).where(func.lower(User.correo) == correo.lower()))

    @staticmethod
    async def get_student_by_matricula(db: AsyncSession, matricula: str) -> Student | None:
        return await db.scalar(select(Student).where(Student.matricula == matricula))

    @staticmethod
    async def get_teacher_by_numero_empleado(db: AsyncSession, numero_empleado: str) -> Teacher | None:
        return await db.scalar(select(Teacher).where(Teacher.numero_empleado == numero_empleado))

    @staticmethod
    async def create_with_profile(db: AsyncSession, usuario: User, profile: Student | Teacher) -> User:
        db.add(usuario)
        await db.flush()
        profile.id_usuario = usuario.id_usuario
        db.add(profile)
        await db.flush()
        await db.commit()
        return usuario

    @staticmethod
    async def list_careers(db: AsyncSession, active_only: bool):
        query = select(Career).order_by(Career.nombre, Career.id_carrera)
        if active_only:
            query = query.where(Career.activo.is_(True))
        return (await db.scalars(query)).all()

    @staticmethod
    async def create_career(db: AsyncSession, career: Career):
        db.add(career)
        await db.flush()
        await db.commit()
        return career

    @staticmethod
    async def list_users(db: AsyncSession, role: str | None, search: str, page: int, page_size: int):
        conditions = []
        if role:
            conditions.append(Role.nombre == role)
        if search:
            conditions.append(
                or_(
                    (func.coalesce(User.nombre, "") + " " + func.coalesce(User.apellidos, "")).icontains(
                        search, autoescape=True
                    ),
                    User.correo.icontains(search, autoescape=True),
                    Student.matricula.icontains(search, autoescape=True),
                    Teacher.numero_empleado.icontains(search, autoescape=True),
                )
            )
        base = select(User).join(Role).outerjoin(Student).outerjoin(Teacher).where(*conditions)
        total = await db.scalar(select(func.count()).select_from(base.subquery()))
        result = await db.execute(
            base.options(
                joinedload(User.rol),
                joinedload(User.estudiante).joinedload(Student.carrera),
                joinedload(User.docente),
            )
            .order_by(User.nombre, User.id_usuario)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.unique().scalars().all(), total

    @staticmethod
    async def summary(db: AsyncSession):
        result = await db.execute(
            select(Role.nombre, func.count(User.id_usuario)).join(User).group_by(Role.nombre)
        )
        counts = dict(result.all())
        careers = await db.scalar(select(func.count()).select_from(Career).where(Career.activo.is_(True)))
        return {
            "estudiantes": counts.get("estudiante", 0),
            "docentes": counts.get("docente", 0),
            "administradores": counts.get("administrador", 0),
            "carreras_activas": careers,
        }
