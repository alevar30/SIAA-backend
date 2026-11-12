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
from app.repositories.auth_repository import AuthRepository
from app.schemas.admin import AltaDocenteRequest, AltaEstudianteRequest

repo = AdminRepository()


class AdminService:
    @staticmethod
    async def _create(
        db: AsyncSession,
        role_name: str,
        profile: Student | Teacher,
        *,
        nombre: str | None = None,
        correo: str | None = None,
    ):
        if correo and await repo.get_user_by_correo(db, correo):
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")
        rol = await repo.get_role_by_name(db, role_name)
        if not rol or not rol.activo:
            raise HTTPException(status_code=409, detail="El rol solicitado no está disponible")
        password = generate_temporary_password(short=isinstance(profile, Student))
        usuario = User(
            id_rol=rol.id_rol,
            nombre=nombre,
            correo=correo,
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
            "nombre": usuario.nombre_completo,
            "correo": usuario.correo,
            "rol": rol.nombre,
            "matricula": profile.matricula if isinstance(profile, Student) else None,
            "password_temporal": password,
            "debe_cambiar_contrasena": True,
            "mensaje": "Cuenta creada. Entrega la contraseña temporal por un canal privado; debe cambiarse al iniciar sesión.",
        }

    @staticmethod
    async def alta_estudiante(db: AsyncSession, datos: AltaEstudianteRequest):
        if await repo.get_student_by_matricula(db, datos.matricula):
            raise HTTPException(status_code=409, detail="Ya existe un estudiante con ese número de control")
        if await repo.get_teacher_by_numero_empleado(db, datos.matricula):
            raise HTTPException(status_code=409, detail="Ese número de control coincide con uno de empleado")
        return await AdminService._create(db, "estudiante", Student(matricula=datos.matricula))

    @staticmethod
    async def alta_docente(db: AsyncSession, datos: AltaDocenteRequest):
        if await repo.get_teacher_by_numero_empleado(db, datos.numero_empleado):
            raise HTTPException(status_code=409, detail="Ya existe un docente con ese número de empleado")
        if await repo.get_student_by_matricula(db, datos.numero_empleado):
            raise HTTPException(status_code=409, detail="Ese número de empleado coincide con uno de control")
        return await AdminService._create(
            db,
            "docente",
            Teacher(
                numero_empleado=datos.numero_empleado,
                departamento=datos.departamento,
            ),
            nombre=datos.nombre,
            correo=str(datos.correo),
        )

    @staticmethod
    async def reset_password(db: AsyncSession, user_id: int, admin: User):
        if user_id == admin.id_usuario:
            raise HTTPException(
                status_code=409, detail="Para cambiar tu contraseña, usa la sección Seguridad"
            )
        user = await AuthRepository.get_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if not user.activo or not user.rol.activo:
            raise HTTPException(status_code=409, detail="La cuenta o el rol está desactivado")
        password = generate_temporary_password(short=True)
        password_hash = await run_in_threadpool(get_password_hash, password)
        if not await AuthRepository.update_password(db, user, password_hash, temporary=True):
            await db.rollback()
            raise HTTPException(
                status_code=409, detail="La cuenta cambió. Consulta su estado antes de reintentar"
            )
        await db.commit()
        return {"password_temporal": password}

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
                    "nombre": user.nombre_completo,
                    "correo": user.correo,
                    "rol": user.rol.nombre,
                    "activo": user.activo,
                    "debe_cambiar_contrasena": user.debe_cambiar_contrasena,
                    "requiere_completar_perfil": user.requiere_completar_perfil,
                    "matricula": student.matricula if student else None,
                    "carrera": student.carrera.nombre if student and student.carrera else None,
                    "semestre": student.semestre if student else None,
                    "numero_empleado": teacher.numero_empleado if teacher else None,
                    "departamento": teacher.departamento if teacher else None,
                }
            )
        return {"items": items, "total": total, "page": page, "page_size": page_size}
