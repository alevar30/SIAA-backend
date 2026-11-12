from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Inicio de sesión por correo, matrícula o número de empleado",
)
async def login(datos: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return await AuthService.login(db, datos)


@router.get("/me", response_model=CurrentUserResponse)
async def me(response: Response, current_user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {
        "id_usuario": current_user.id_usuario,
        "nombre": current_user.nombre,
        "correo": current_user.correo,
        "rol": current_user.rol.nombre,
        "debe_cambiar_contrasena": current_user.debe_cambiar_contrasena,
        "id_estudiante": current_user.estudiante.id_estudiante if current_user.estudiante else None,
        "id_docente": current_user.docente.id_docente if current_user.docente else None,
    }


@router.post("/cambiar-contrasena", response_model=ChangePasswordResponse)
async def cambiar_contrasena(
    datos: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AuthService.cambiar_contrasena(db, current_user, datos)
