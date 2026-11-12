from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import CareerResponse
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    CompleteStudentProfileRequest,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Acceso con número de control, número de empleado o correo de personal",
)
async def login(datos: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return await AuthService.login(db, datos)


@router.get("/me", response_model=CurrentUserResponse)
async def me(response: Response, current_user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    student = current_user.estudiante
    return {
        "id_usuario": current_user.id_usuario,
        "nombre": current_user.nombre_completo,
        "correo": current_user.correo,
        "rol": current_user.rol.nombre,
        "debe_cambiar_contrasena": current_user.debe_cambiar_contrasena,
        "requiere_completar_perfil": current_user.requiere_completar_perfil,
        "matricula": student.matricula if student else None,
        "carrera": student.carrera.nombre if student and student.carrera else None,
        "id_estudiante": student.id_estudiante if student else None,
        "id_docente": current_user.docente.id_docente if current_user.docente else None,
    }


@router.post("/cambiar-contrasena", response_model=ChangePasswordResponse)
async def cambiar_contrasena(
    datos: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AuthService.cambiar_contrasena(db, current_user, datos)


@router.get("/primer-acceso/carreras", response_model=list[CareerResponse])
async def onboarding_careers(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.rol.nombre != "estudiante" or not current_user.requiere_completar_perfil:
        raise HTTPException(status_code=403, detail="El catálogo de primer acceso no está disponible")
    response.headers["Cache-Control"] = "no-store"
    return await AdminRepository.list_careers(db, active_only=True)


@router.post("/primer-acceso", response_model=ChangePasswordResponse)
async def complete_student_profile(
    datos: CompleteStudentProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AuthService.complete_student_profile(db, current_user, datos)
