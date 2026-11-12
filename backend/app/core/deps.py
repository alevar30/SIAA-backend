from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.auth_repository import AuthRepository

bearer_scheme = HTTPBearer(auto_error=False)
repo = AuthRepository()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise error
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise error
    subject, version = payload.get("sub"), payload.get("ver")
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal():
        raise error
    if len(subject) > 19 or int(subject) < 1 or int(subject) > 9223372036854775807:
        raise error
    if type(version) is not int or version < 1:
        raise error
    usuario = await repo.get_by_id(db, int(subject))
    if usuario is None or usuario.token_version != version:
        raise error
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    if not usuario.rol or not usuario.rol.activo:
        raise HTTPException(status_code=403, detail="Rol no disponible")
    return usuario


async def get_ready_user(current_user: User = Depends(get_current_user)) -> User:
    """Usar en todas las futuras rutas de negocio; /me y cambio permiten acceso limitado."""
    if current_user.debe_cambiar_contrasena:
        raise HTTPException(status_code=403, detail="Debes cambiar tu contraseña antes de continuar")
    return current_user


def require_roles(*allowed_roles: str):
    allowed = {role.casefold() for role in allowed_roles}

    async def role_checker(current_user: User = Depends(get_ready_user)) -> User:
        if current_user.rol.nombre.casefold() not in allowed:
            raise HTTPException(status_code=403, detail="No tienes permisos para esta operación")
        return current_user

    return role_checker


require_admin = require_roles("administrador")
require_docente = require_roles("docente")
require_estudiante = require_roles("estudiante")
require_admin_or_docente = require_roles("administrador", "docente")
