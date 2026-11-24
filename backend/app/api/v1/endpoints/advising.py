from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_ready_user, require_admin_or_docente, require_docente, require_estudiante
from app.db.session import get_db
from app.models.advising import AdvisingSession, Availability, Participant
from app.models.user import User
from app.repositories.advising_repository import AdvisingRepository as repo, now_utc
from app.schemas.advising import (
    AttendanceInput,
    AvailabilityCreate,
    AvailabilityRead,
    CancelInput,
    SessionCreate,
    SessionDetail,
    SessionList,
    VersionInput,
)
from app.services.advising_service import AdvisingService as service

router = APIRouter(tags=["Agenda y asesorías"])
ScheduleId = Annotated[int, Path(gt=0, le=2147483647)]


@router.get("/docente/disponibilidades", response_model=list[AvailabilityRead])
async def availability(db: AsyncSession = Depends(get_db), user: User = Depends(require_docente)):
    rows = (
        await db.scalars(
            select(Availability)
            .where(
                Availability.id_docente == user.docente.id_docente,
                Availability.estado == "activa",
                Availability.fin > now_utc(),
            )
            .order_by(Availability.inicio)
            .limit(200)
        )
    ).all()
    return [service.availability_record(row) for row in rows]


@router.post("/docente/disponibilidades", response_model=AvailabilityRead, status_code=201)
async def create_availability(
    data: AvailabilityCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_docente)
):
    return await service.create_availability(db, user, data)


@router.put("/docente/disponibilidades/{id_}/cancelar", response_model=AvailabilityRead)
async def cancel_availability(
    id_: ScheduleId,
    data: VersionInput,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_docente),
):
    return await service.cancel_availability(db, user, id_, data)


@router.post("/docente/asesorias", response_model=SessionDetail, status_code=201)
async def create_session(
    data: SessionCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_docente)
):
    return await service.create_session(db, user, data)


async def session_list(db, user, query, page, page_size):
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (
        await db.execute(
            query.order_by(AdvisingSession.inicio, AdvisingSession.id_asesoria)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return dict(items=await repo.records(db, rows, user), total=total, page=page, page_size=page_size)


@router.get("/asesorias/disponibles", response_model=SessionList)
async def available_sessions(
    id_docente: int | None = Query(None, gt=0, le=9223372036854775807),
    id_materia: int | None = Query(None, gt=0, le=2147483647),
    id_tema: int | None = Query(None, gt=0, le=2147483647),
    page: int = Query(1, ge=1, le=1000000),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_ready_user),
):
    from app.models.academic import Topic

    query = repo.query().where(
        AdvisingSession.estado == "programada", AdvisingSession.inicio > now_utc(), *repo.visible_topic()
    )
    if id_docente:
        query = query.where(AdvisingSession.id_docente == id_docente)
    if id_materia:
        query = query.where(Topic.id_materia == id_materia)
    if id_tema:
        query = query.where(AdvisingSession.id_tema == id_tema)
    return await session_list(db, user, query, page, page_size)


@router.get("/asesorias/mias", response_model=SessionList)
async def own_sessions(
    vista: Literal["proximas", "historial"] = "proximas",
    page: int = Query(1, ge=1, le=1000000),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_ready_user),
):
    query = repo.query()
    past = or_(AdvisingSession.fin <= now_utc(), AdvisingSession.estado != "programada")
    if user.rol.nombre == "docente":
        query = query.where(AdvisingSession.id_docente == user.docente.id_docente)
    elif user.rol.nombre == "estudiante":
        query = query.join(Participant, Participant.id_asesoria == AdvisingSession.id_asesoria).where(
            Participant.id_estudiante == user.estudiante.id_estudiante
        )
        past = or_(past, Participant.estado == "cancelada")
    query = query.where(past if vista == "historial" else ~past)
    return await session_list(db, user, query, page, page_size)


@router.get("/asesorias/{id_}", response_model=SessionDetail)
async def detail(id_: ScheduleId, db: AsyncSession = Depends(get_db), user: User = Depends(get_ready_user)):
    row = await db.get(AdvisingSession, id_)
    if row is None:
        raise HTTPException(404, "Asesoría no encontrada")
    if user.rol.nombre != "administrador" and not (
        user.docente and user.docente.id_docente == row.id_docente
    ):
        participant = await db.scalar(
            select(Participant.id_participante).where(
                Participant.id_asesoria == id_,
                Participant.id_estudiante == user.estudiante.id_estudiante if user.estudiante else False,
            )
        )
        visible = await db.scalar(
            repo.query()
            .with_only_columns(AdvisingSession.id_asesoria)
            .where(
                AdvisingSession.id_asesoria == id_,
                AdvisingSession.estado == "programada",
                AdvisingSession.inicio > now_utc(),
                *repo.visible_topic(),
            )
        )
        if not participant and not visible:
            raise HTTPException(404, "Asesoría no encontrada")
    return await repo.detail(db, id_, user)


@router.post("/asesorias/{id_}/reservar", response_model=SessionDetail)
async def reserve(
    id_: ScheduleId, db: AsyncSession = Depends(get_db), user: User = Depends(require_estudiante)
):
    return await service.reserve(db, user, id_)


@router.put("/asesorias/{id_}/cancelar-reserva", response_model=SessionDetail)
async def cancel_reservation(
    id_: ScheduleId,
    data: VersionInput,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_estudiante),
):
    return await service.cancel_reservation(db, user, id_, data)


@router.put("/asesorias/{id_}/cancelar", response_model=SessionDetail)
async def cancel_session(
    id_: ScheduleId,
    data: CancelInput,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin_or_docente),
):
    return await service.cancel_session(db, user, id_, data)


@router.put("/asesorias/{id_}/finalizar", response_model=SessionDetail)
async def finalize(
    id_: ScheduleId,
    data: AttendanceInput,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_docente),
):
    return await service.finalize(db, user, id_, data)
