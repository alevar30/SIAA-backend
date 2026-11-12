from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import create_access_token, get_password_hash, verify_password
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest

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
            "nombre": usuario.nombre,
            "rol": usuario.rol.nombre,
        }

    @staticmethod
    async def cambiar_contrasena(db: AsyncSession, usuario, datos: ChangePasswordRequest):
        expected_version = usuario.token_version
        if datos.password_nueva != datos.password_nueva_confirm:
            raise HTTPException(status_code=400, detail="Las contraseñas nuevas no coinciden")
        if not await run_in_threadpool(verify_password, datos.password_actual, usuario.password_hash):
            raise HTTPException(status_code=400, detail="Contraseña actual inválida")
        if datos.password_actual == datos.password_nueva:
            raise HTTPException(status_code=400, detail="La nueva contraseña debe ser diferente de la actual")
        new_hash = await run_in_threadpool(get_password_hash, datos.password_nueva)
        if not await repo.update_password(db, usuario, new_hash, expected_version):
            raise HTTPException(
                status_code=401,
                detail="La sesión cambió; inicia sesión nuevamente",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "message": "Contraseña actualizada. Inicia sesión nuevamente.",
            "debe_cambiar_contrasena": False,
            "requiere_nuevo_login": True,
        }
