from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import AltaDocenteRequest, AltaEstudianteRequest, UsuarioCreadoResponse
from app.services.admin_service import AdminService

router = APIRouter()


@router.post("/estudiantes", response_model=UsuarioCreadoResponse, status_code=status.HTTP_201_CREATED)
async def alta_estudiante(
    datos: AltaEstudianteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Solo el administrador puede dar de alta estudiantes."""
    return await AdminService.alta_estudiante(db, datos)


@router.post("/docentes", response_model=UsuarioCreadoResponse, status_code=status.HTTP_201_CREATED)
async def alta_docente(
    datos: AltaDocenteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Solo el administrador puede dar de alta docentes."""
    return await AdminService.alta_docente(db, datos)
