from datetime import datetime, timezone

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Career, CareerSubject, Subject, TeacherTopic, Topic
from app.models.advising import AdvisingSession, Availability, Participant
from app.models.profiles import Student, Teacher
from app.models.user import Role, User


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AdvisingRepository:
    @staticmethod
    def visible_topic():
        return (
            Topic.activo.is_(True),
            Subject.activo.is_(True),
            exists(
                select(CareerSubject.id_carrera)
                .join(Career)
                .where(CareerSubject.id_materia == Subject.id_materia, Career.activo.is_(True))
            ),
            exists(
                select(TeacherTopic.id_tema).where(
                    TeacherTopic.id_docente == AdvisingSession.id_docente,
                    TeacherTopic.id_tema == Topic.id_tema,
                )
            ),
            User.activo.is_(True),
            Role.activo.is_(True),
            Role.nombre == "docente",
        )

    @staticmethod
    def query():
        return (
            select(AdvisingSession, Availability, Topic, Subject, User)
            .join(Availability, Availability.id_disponibilidad == AdvisingSession.id_disponibilidad)
            .join(Topic, Topic.id_tema == AdvisingSession.id_tema)
            .join(Subject, Subject.id_materia == Topic.id_materia)
            .join(Teacher, Teacher.id_docente == AdvisingSession.id_docente)
            .join(User, User.id_usuario == Teacher.id_usuario)
            .join(Role, Role.id_rol == User.id_rol)
        )

    @staticmethod
    async def records(db: AsyncSession, rows, user: User):
        ids = [row[0].id_asesoria for row in rows]
        if not ids:
            return []
        counts = dict(
            (
                await db.execute(
                    select(Participant.id_asesoria, func.count())
                    .where(Participant.id_asesoria.in_(ids), Participant.estado != "cancelada")
                    .group_by(Participant.id_asesoria)
                )
            ).all()
        )
        student_id = user.estudiante.id_estudiante if user.estudiante else None
        reservations = {}
        if student_id:
            reservations = {
                p.id_asesoria: p
                for p in (
                    await db.scalars(
                        select(Participant).where(
                            Participant.id_asesoria.in_(ids), Participant.id_estudiante == student_id
                        )
                    )
                ).all()
            }
        items = []
        for session, availability, topic, subject, teacher_user in rows:
            reservation = reservations.get(session.id_asesoria)
            occupied = counts.get(session.id_asesoria, 0)
            location = availability.ubicacion
            can_view_link = (
                user.rol.nombre == "administrador"
                or (user.docente and user.docente.id_docente == session.id_docente)
                or (reservation is not None and reservation.estado != "cancelada")
            )
            if availability.modalidad == "virtual" and not can_view_link:
                location = "El enlace estará disponible al reservar"
            items.append(
                dict(
                    id_asesoria=session.id_asesoria,
                    id_docente=session.id_docente,
                    docente=teacher_user.nombre_completo,
                    materia=subject.nombre,
                    id_materia=subject.id_materia,
                    tema=topic.nombre,
                    id_tema=topic.id_tema,
                    inicio=utc(session.inicio),
                    fin=utc(session.fin),
                    modalidad=availability.modalidad,
                    ubicacion=location,
                    tipo=session.tipo,
                    cupo_maximo=session.cupo_maximo,
                    ocupados=occupied,
                    disponibles=max(0, session.cupo_maximo - occupied)
                    if session.estado == "programada"
                    else 0,
                    estado=session.estado,
                    motivo_cancelacion=session.motivo_cancelacion,
                    version=session.version,
                    mi_reserva=dict(estado=reservation.estado, version=reservation.version)
                    if reservation
                    else None,
                )
            )
        return items

    @staticmethod
    async def detail(db: AsyncSession, id_: int, user: User):
        row = (await db.execute(AdvisingRepository.query().where(AdvisingSession.id_asesoria == id_))).one()
        result = (await AdvisingRepository.records(db, [row], user))[0]
        result["participantes"] = []
        if user.rol.nombre == "administrador" or (
            user.docente and user.docente.id_docente == row[0].id_docente
        ):
            participants = (
                await db.execute(
                    select(Participant, Student, User)
                    .join(Student, Student.id_estudiante == Participant.id_estudiante)
                    .join(User, User.id_usuario == Student.id_usuario)
                    .where(Participant.id_asesoria == id_)
                    .order_by(Student.matricula)
                )
            ).all()
            result["participantes"] = [
                dict(
                    id_estudiante=s.id_estudiante,
                    nombre=u.nombre_completo,
                    matricula=s.matricula,
                    estado=p.estado,
                )
                for p, s, u in participants
            ]
        return result
