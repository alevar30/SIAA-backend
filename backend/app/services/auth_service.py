from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.academic import Career
from app.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import ChangePasswordRequest, CompleteStudentProfileRequest, LoginRequest

repo = AuthRepository()
# Hash válido para que un identificador inexistente también haga una verificación bcrypt.
DUMMY_HASH = "$2b$12$R9h/cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jWMUW"


class AuthService:
    @staticmethod
    async def login(db: AsyncSession, datos: LoginRequest):
        usuario = await repo.get_by_identifier(db, datos.identificador)
        valid = await run_in_threadpool(
            verify_password,
            datos.password,
            usuario.password_hash if usuario else DUMMY_HASH,
        )
        if not usuario or not valid:
            raise HTTPException(
                status_code=401, detail="Credenciales inválidas", headers={"WWW-Authenticate": "Bearer"}
            )
        if not usuario.activo or not usuario.rol or not usuario.rol.activo:
            raise HTTPException(status_code=403, detail="Cuenta o rol desactivado")
        token = create_access_token({"sub": str(usuario.id_usuario), "ver": usuario.token_version})
        return {
            "access_token": token,
            "token_type": "bearer",
            "debe_cambiar_contrasena": usuario.debe_cambiar_contrasena,
            "requiere_cambio_contrasena": usuario.debe_cambiar_contrasena,
            "id_usuario": usuario.id_usuario,
            "nombre": usuario.nombre_completo,
            "rol": usuario.rol.nombre,
        }

    @staticmethod
    async def _change_password(db: AsyncSession, usuario: User, datos: ChangePasswordRequest):
        if datos.password_nueva != datos.password_nueva_confirm:
            raise HTTPException(status_code=400, detail="Las contraseñas nuevas no coinciden")
        if not await run_in_threadpool(verify_password, datos.password_actual, usuario.password_hash):
            raise HTTPException(status_code=400, detail="Contraseña actual inválida")
        if datos.password_actual == datos.password_nueva:
            raise HTTPException(status_code=400, detail="La nueva contraseña debe ser diferente de la actual")
        new_hash = await run_in_threadpool(get_password_hash, datos.password_nueva)
        if not await repo.update_password(db, usuario, new_hash):
            await db.rollback()
            raise HTTPException(
                status_code=401,
                detail="La sesión cambió; inicia sesión nuevamente",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    async def cambiar_contrasena(db: AsyncSession, usuario: User, datos: ChangePasswordRequest):
        if usuario.requiere_completar_perfil:
            raise HTTPException(status_code=409, detail="Completa tu perfil para establecer tu contraseña")
        await AuthService._change_password(db, usuario, datos)
        await db.commit()
        return {
            "message": "Contraseña actualizada. Inicia sesión nuevamente.",
            "debe_cambiar_contrasena": False,
            "requiere_nuevo_login": True,
        }

    @staticmethod
    async def complete_student_profile(db: AsyncSession, usuario: User, datos: CompleteStudentProfileRequest):
        student = usuario.estudiante
        if usuario.rol.nombre != "estudiante" or student is None:
            raise HTTPException(status_code=403, detail="Solo los estudiantes pueden completar este perfil")
        if not usuario.requiere_completar_perfil:
            raise HTTPException(status_code=409, detail="Tu perfil ya está completo")
        career = await db.get(Career, datos.id_carrera)
        if career is None or not career.activo:
            raise HTTPException(status_code=409, detail="Selecciona una carrera activa")
        await AuthService._change_password(db, usuario, datos)
        usuario.nombre = datos.nombre
        usuario.apellidos = datos.apellidos
        student.id_carrera = career.id_carrera
        await db.commit()
        return {
            "message": "Perfil guardado. Inicia sesión con tu nueva contraseña.",
            "debe_cambiar_contrasena": False,
            "requiere_nuevo_login": True,
        }
