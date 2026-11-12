from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.user import User
from app.models.profiles import Student, Teacher


class AuthRepository:
    @staticmethod
    async def get_by_identifier(db: AsyncSession, identifier: str) -> User | None:
        result = await db.execute(
            select(User)
            .outerjoin(Student)
            .outerjoin(Teacher)
            .options(joinedload(User.rol))
            .where(
                or_(
                    func.lower(User.correo) == identifier.lower(),
                    Student.matricula == identifier,
                    Teacher.numero_empleado == identifier,
                )
            )
        )
        users = result.unique().scalars().all()
        # Una colisión de identificadores nunca debe seleccionar otra cuenta arbitrariamente.
        return users[0] if len(users) == 1 else None

    @staticmethod
    async def get_by_id(db: AsyncSession, id_usuario: int) -> User | None:
        result = await db.execute(
            select(User)
            .options(joinedload(User.rol), joinedload(User.estudiante), joinedload(User.docente))
            .where(User.id_usuario == id_usuario)
        )
        return result.unique().scalar_one_or_none()

    @staticmethod
    async def update_password(db: AsyncSession, usuario: User, new_hash: str, expected_version: int) -> bool:
        result = await db.execute(
            update(User)
            .where(User.id_usuario == usuario.id_usuario, User.token_version == expected_version)
            .values(
                password_hash=new_hash,
                debe_cambiar_contrasena=False,
                fecha_ultimo_cambio=datetime.now(timezone.utc).replace(tzinfo=None),
                token_version=User.token_version + 1,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            await db.rollback()
            return False
        await db.commit()
        return True
