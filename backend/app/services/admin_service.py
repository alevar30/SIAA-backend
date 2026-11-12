from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import generate_temporary_password, get_password_hash
from app.models.user import User
from app.models.academic import Career
from sqlalchemy import func, select
from app.models.profiles import Student, Teacher
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import AltaDocenteRequest, AltaEstudianteRequest

repo = AdminRepository()


class AdminService:
    @staticmethod
    async def _create(db: AsyncSession, datos, role_name: str, profile: Student | Teacher):
        if await repo.get_user_by_correo(db, datos.correo):
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")
        rol = await repo.get_role_by_name(db, role_name)
        if not rol or not rol.activo:
            raise HTTPException(status_code=409, detail="El rol solicitado no está disponible")
        password = generate_temporary_password()
        usuario = User(
            id_rol=rol.id_rol,
            nombre=datos.nombre,
            correo=str(datos.correo),
            password_hash=await run_in_threadpool(get_password_hash, password),
            activo=True,
            debe_cambiar_contrasena=True,
        )
        try:
            usuario = await repo.create_with_profile(db, usuario, profile)
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                status_code=409,
                detail="No se pudo crear la cuenta: datos duplicados o referencias no disponibles",
            ) from exc
        return {
            "id_usuario": usuario.id_usuario,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "rol": rol.nombre,
            "password_temporal": password,
            "debe_cambiar_contrasena": True,
            "mensaje": "Cuenta creada. Entrega la contraseña temporal por un canal privado; debe cambiarse al iniciar sesión.",
        }

    @staticmethod
    async def alta_estudiante(db: AsyncSession, datos: AltaEstudianteRequest):
        career = await repo.get_career(db, datos.id_carrera)
        if career is None:
            raise HTTPException(status_code=404, detail="Carrera no encontrada")
        if not career.activo:
            raise HTTPException(status_code=409, detail="La carrera está desactivada")
        if await repo.get_student_by_matricula(db, datos.matricula):
            raise HTTPException(status_code=409, detail="Ya existe un estudiante con esa matrícula")
        return await AdminService._create(
            db,
            datos,
            "estudiante",
            Student(
                id_carrera=datos.id_carrera,
                matricula=datos.matricula,
                semestre=datos.semestre,
            ),
        )

    @staticmethod
    async def alta_docente(db: AsyncSession, datos: AltaDocenteRequest):
        if await repo.get_teacher_by_numero_empleado(db, datos.numero_empleado):
            raise HTTPException(status_code=409, detail="Ya existe un docente con ese número de empleado")
        return await AdminService._create(
            db,
            datos,
            "docente",
            Teacher(
                numero_empleado=datos.numero_empleado,
                departamento=datos.departamento,
            ),
        )

    @staticmethod
    async def create_career(db: AsyncSession, datos):
        if await db.scalar(select(Career).where(func.upper(Career.clave) == datos.clave)):
            raise HTTPException(status_code=409, detail="Ya existe una carrera con esa clave")
        try:
            return await repo.create_career(db, Career(nombre=datos.nombre, clave=datos.clave, activo=True))
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Ya existe una carrera con esa clave") from exc

    @staticmethod
    async def list_users(db: AsyncSession, role: str | None, search: str, page: int, page_size: int):
        users, total = await repo.list_users(db, role, search.strip(), page, page_size)
        items = []
        for user in users:
            student, teacher = user.estudiante, user.docente
            items.append(
                {
                    "id_usuario": user.id_usuario,
                    "nombre": user.nombre,
                    "correo": user.correo,
                    "rol": user.rol.nombre,
                    "activo": user.activo,
                    "debe_cambiar_contrasena": user.debe_cambiar_contrasena,
                    "matricula": student.matricula if student else None,
                    "carrera": student.carrera.nombre if student else None,
                    "semestre": student.semestre if student else None,
                    "numero_empleado": teacher.numero_empleado if teacher else None,
                    "departamento": teacher.departamento if teacher else None,
                }
            )
        return {"items": items, "total": total, "page": page, "page_size": page_size}
