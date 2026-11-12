from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AltaDocenteRequest,
    AltaEstudianteRequest,
    TemporaryPasswordResponse,
    UsuarioCreadoResponse,
)
from app.services.admin_service import AdminService
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import CareerResponse, CareerCreateRequest, UserListResponse, AdminSummaryResponse

router = APIRouter()


@router.post("/estudiantes", response_model=UsuarioCreadoResponse, status_code=status.HTTP_201_CREATED)
async def alta_estudiante(
    datos: AltaEstudianteRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Solo el administrador puede dar de alta estudiantes."""
    response.headers["Cache-Control"] = "no-store"
    return await AdminService.alta_estudiante(db, datos)


@router.post("/docentes", response_model=UsuarioCreadoResponse, status_code=status.HTTP_201_CREATED)
async def alta_docente(
    datos: AltaDocenteRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Solo el administrador puede dar de alta docentes."""
    response.headers["Cache-Control"] = "no-store"
    return await AdminService.alta_docente(db, datos)


@router.get("/carreras", response_model=list[CareerResponse])
async def list_careers(
    response: Response,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    response.headers["Cache-Control"] = "no-store"
    return await AdminRepository.list_careers(db, active_only)


@router.post("/carreras", response_model=CareerResponse, status_code=201)
async def create_career(
    datos: CareerCreateRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    response.headers["Cache-Control"] = "no-store"
    return await AdminService.create_career(db, datos)


@router.get("/usuarios", response_model=UserListResponse)
async def list_users(
    response: Response,
    rol: Literal["estudiante", "docente", "administrador"] | None = None,
    q: str = Query(default="", max_length=150),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    response.headers["Cache-Control"] = "no-store"
    return await AdminService.list_users(db, rol, q, page, page_size)


@router.get("/resumen", response_model=AdminSummaryResponse)
async def summary(
    response: Response, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_admin)
):
    response.headers["Cache-Control"] = "no-store"
    return await AdminRepository.summary(db)


@router.post("/usuarios/{user_id}/restablecer-contrasena", response_model=TemporaryPasswordResponse)
async def reset_password(
    user_id: Annotated[int, Path(ge=1, le=9223372036854775807)],
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    response.headers["Cache-Control"] = "no-store"
    return await AdminService.reset_password(db, user_id, current_user)
