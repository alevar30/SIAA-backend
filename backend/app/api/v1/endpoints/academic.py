from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_ready_user, require_admin, require_docente
from app.db.session import get_db
from app.models.user import User
from app.repositories.academic_repository import AcademicRepository as repo
from app.schemas.academic import (
    AssignmentWrite,
    CareerEdit,
    CareerRead,
    SubjectEdit,
    SubjectRead,
    SubjectWrite,
    TeacherList,
    TeacherRead,
    TopicCreate,
    TopicEdit,
    TopicRead,
    TopicSelectionWrite,
)
from app.services.academic_service import AcademicService as service


async def no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"


admin_router = APIRouter(prefix="/admin/catalogo", dependencies=[Depends(require_admin), Depends(no_store)])
public_router = APIRouter(prefix="/catalogo", dependencies=[Depends(get_ready_user), Depends(no_store)])
teacher_router = APIRouter(prefix="/docente", dependencies=[Depends(require_docente), Depends(no_store)])
AcademicPath = Annotated[int, Path(ge=1, le=2147483647)]
TeacherPath = Annotated[int, Path(ge=1, le=9223372036854775807)]


@admin_router.get("/carreras", response_model=list[CareerRead])
async def careers(db: AsyncSession = Depends(get_db)):
    return await repo.careers(db)


@admin_router.put("/carreras/{career_id}", response_model=CareerRead)
async def edit_career(career_id: AcademicPath, data: CareerEdit, db: AsyncSession = Depends(get_db)):
    return await service.update_career(db, career_id, data)


@admin_router.get("/materias", response_model=list[SubjectRead])
async def subjects(db: AsyncSession = Depends(get_db)):
    return await repo.subjects(db)


@admin_router.post("/materias", response_model=SubjectRead, status_code=201)
async def create_subject(data: SubjectWrite, db: AsyncSession = Depends(get_db)):
    return await service.write_subject(db, data)


@admin_router.put("/materias/{subject_id}", response_model=SubjectRead)
async def edit_subject(subject_id: AcademicPath, data: SubjectEdit, db: AsyncSession = Depends(get_db)):
    return await service.write_subject(db, data, subject_id)


@admin_router.get("/materias/{subject_id}/temas", response_model=list[TopicRead])
async def topics(subject_id: AcademicPath, db: AsyncSession = Depends(get_db)):
    from app.models.academic import Subject

    if await db.get(Subject, subject_id) is None:
        raise HTTPException(404, "Materia no encontrada")
    return await repo.topics(db, subject_id)


@admin_router.post("/temas", response_model=TopicRead, status_code=201)
async def create_topic(
    data: TopicCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_admin)
):
    return await service.write_topic(db, data, user=user)


@admin_router.put("/temas/{topic_id}", response_model=TopicRead)
async def edit_topic(
    topic_id: AcademicPath,
    data: TopicEdit,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    return await service.write_topic(db, data, topic_id, user=user)


@teacher_router.post("/temas", response_model=TopicRead, status_code=201)
async def create_own_topic(
    data: TopicCreate, user: User = Depends(require_docente), db: AsyncSession = Depends(get_db)
):
    return await service.write_topic(db, data, user=user)


@teacher_router.put("/temas/{topic_id}", response_model=TopicRead)
async def edit_own_topic(
    topic_id: AcademicPath,
    data: TopicEdit,
    user: User = Depends(require_docente),
    db: AsyncSession = Depends(get_db),
):
    return await service.write_topic(db, data, topic_id, user=user)


@admin_router.get("/docentes", response_model=TeacherList)
async def teachers(
    q: str = Query(default="", max_length=150),
    page: int = Query(default=1, ge=1, le=2147483647),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await repo.teachers(db, q.strip(), page, page_size)


@admin_router.get("/docentes/{teacher_id}", response_model=TeacherRead)
async def teacher(teacher_id: TeacherPath, db: AsyncSession = Depends(get_db)):
    return await service.teacher(db, teacher_id)


@admin_router.put("/docentes/{teacher_id}/materias", response_model=TeacherRead)
async def assign(teacher_id: TeacherPath, data: AssignmentWrite, db: AsyncSession = Depends(get_db)):
    return await service.assign_subjects(db, teacher_id, data)


@teacher_router.get("/materias", response_model=TeacherRead)
async def own_subjects(user: User = Depends(require_docente), db: AsyncSession = Depends(get_db)):
    if user.docente is None:
        raise HTTPException(404, "Perfil docente no encontrado")
    return await service.teacher(db, user.docente.id_docente)


@teacher_router.put("/temas", response_model=TeacherRead)
async def own_topics(
    data: TopicSelectionWrite, user: User = Depends(require_docente), db: AsyncSession = Depends(get_db)
):
    if user.docente is None:
        raise HTTPException(404, "Perfil docente no encontrado")
    return await service.select_topics(db, user.docente.id_docente, data)


@public_router.get("/carreras", response_model=list[CareerRead])
async def available_careers(db: AsyncSession = Depends(get_db)):
    return await repo.careers(db, active_only=True)


@public_router.get("/materias", response_model=list[SubjectRead])
async def available_subjects(
    id_carrera: int | None = Query(default=None, ge=1, le=2147483647), db: AsyncSession = Depends(get_db)
):
    return await repo.subjects(db, active_only=True, career_id=id_carrera)


@public_router.get("/materias/{subject_id}/temas", response_model=list[TopicRead])
async def available_topics(subject_id: AcademicPath, db: AsyncSession = Depends(get_db)):
    return await repo.topics(db, subject_id, active_only=True)


@public_router.get("/docentes", response_model=TeacherList)
async def compatible_teachers(
    id_materia: int = Query(ge=1, le=2147483647),
    id_tema: int = Query(ge=1, le=2147483647),
    page: int = Query(default=1, ge=1, le=2147483647),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await service.search_teachers(db, id_materia, id_tema, page, page_size)
