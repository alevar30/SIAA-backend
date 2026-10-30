from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.auth_repository import AuthRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

repo = AuthRepository()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    id_usuario = payload.get("id_usuario") or payload.get("sub")
    if id_usuario is None:
        raise credentials_exception

    try:
        id_usuario_int = int(id_usuario)
    except (TypeError, ValueError):
        raise credentials_exception

    usuario = await repo.get_by_id(db, id_usuario_int)
    if usuario is None:
        raise credentials_exception

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado",
        )

    return usuario


def require_roles(*allowed_roles: str):
    """
    Dependencia para restringir acceso por rol.
    Uso: dependencies=[Depends(require_roles("administrador"))]
    o current_user: User = Depends(require_roles("administrador", "docente"))
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.rol:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sin rol asignado",
            )

        rol_nombre = current_user.rol.nombre.lower()
        allowed = [r.lower() for r in allowed_roles]

        if rol_nombre not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado. Solo permitido para: " + ", ".join(allowed_roles),
            )

        return current_user

    return role_checker


# Atajos comunes
require_admin = require_roles("administrador")
require_docente = require_roles("docente")
require_estudiante = require_roles("estudiante")
require_admin_or_docente = require_roles("administrador", "docente")

