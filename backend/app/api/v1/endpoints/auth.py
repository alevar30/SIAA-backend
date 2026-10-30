from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=LoginResponse, summary="Inicio de sesión flexible")
async def login(datos: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Permite iniciar sesión con:
    - Correo electrónico
    - Matrícula (para estudiantes)
    - Número de empleado (para docentes)
    """
    return await AuthService.login(db, datos)


@router.post("/cambiar-contrasena", summary="Cambiar contraseña tras primer inicio")
async def cambiar_contrasena(
    datos: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Requiere token Bearer. Obligatorio cuando debe_cambiar_contrasena = true.
    """
    return await AuthService.cambiar_contrasena(db, current_user.id_usuario, datos)
