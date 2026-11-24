from fastapi import HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Career, CareerSubject, Subject, TeacherTopic, Topic
from app.models.advising import AdvisingSession, Availability, Participant
from app.models.profiles import Student, Teacher
from app.repositories.advising_repository import AdvisingRepository as repo, now_utc, utc
from app.services.academic_service import AcademicService


class AdvisingService:
    @staticmethod
    async def lock_teacher(db: AsyncSession, id_: int):
        teacher = await db.scalar(
            select(Teacher)
            .where(Teacher.id_docente == id_)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if teacher is None:
            raise HTTPException(404, "Docente no encontrado")
        return teacher

    @staticmethod
    def check_version(record, version: int):
        if record.version != version:
            raise HTTPException(409, "El registro cambió. Recarga antes de continuar.")

    @staticmethod
    async def create_availability(db, user, data):
        teacher_id = user.docente.id_docente
        await AdvisingService.lock_teacher(db, teacher_id)
        overlap = await db.scalar(
            select(Availability.id_disponibilidad)
            .where(
                Availability.id_docente == teacher_id,
                Availability.estado == "activa",
                Availability.inicio < data.fin,
                Availability.fin > data.inicio,
            )
            .limit(1)
        )
        if overlap:
            raise HTTPException(409, "Este horario se cruza con otra disponibilidad activa")
        row = Availability(id_docente=teacher_id, **data.model_dump())
        db.add(row)
        await AcademicService.commit(db)
        await db.refresh(row)
        return AdvisingService.availability_record(row)

    @staticmethod
    def availability_record(row):
        return dict(
            id_disponibilidad=row.id_disponibilidad,
            inicio=utc(row.inicio),
            fin=utc(row.fin),
            modalidad=row.modalidad,
            ubicacion=row.ubicacion,
            estado=row.estado,
            version=row.version,
        )

    @staticmethod
    async def cancel_availability(db, user, id_, data):
        await AdvisingService.lock_teacher(db, user.docente.id_docente)
        row = await db.get(Availability, id_, populate_existing=True)
        if row is None or row.id_docente != user.docente.id_docente:
            raise HTTPException(404, "Disponibilidad no encontrada")
        AdvisingService.check_version(row, data.version)
        if row.estado != "activa" or utc(row.fin) <= now_utc():
            raise HTTPException(409, "Este horario ya no se puede retirar")
        if await db.scalar(
            select(AdvisingSession.id_asesoria)
            .where(
                AdvisingSession.id_disponibilidad == id_,
                AdvisingSession.estado == "programada",
            )
            .limit(1)
        ):
            raise HTTPException(409, "Cancela o finaliza sus asesorías antes de retirar el horario")
        row.estado = "cancelada"
        row.version += 1
        await AcademicService.commit(db)
        return AdvisingService.availability_record(row)

    @staticmethod
    async def create_session(db, user, data):
        teacher_id = user.docente.id_docente
        await AdvisingService.lock_teacher(db, teacher_id)
        slot = await db.get(Availability, data.id_disponibilidad, populate_existing=True)
        if slot is None or slot.id_docente != teacher_id:
            raise HTTPException(404, "Disponibilidad no encontrada")
        if slot.estado != "activa" or not utc(slot.inicio) <= data.inicio < data.fin <= utc(slot.fin):
            raise HTTPException(409, "La asesoría debe quedar dentro de una disponibilidad activa propia")
        topic = await db.scalar(
            select(Topic)
            .join(Subject)
            .join(TeacherTopic, TeacherTopic.id_tema == Topic.id_tema)
            .where(
                Topic.id_tema == data.id_tema,
                TeacherTopic.id_docente == teacher_id,
                Topic.activo.is_(True),
                Subject.activo.is_(True),
                exists(
                    select(CareerSubject.id_carrera)
                    .join(Career)
                    .where(CareerSubject.id_materia == Subject.id_materia, Career.activo.is_(True))
                ),
            )
            .with_for_update(of=Topic)
        )
        if topic is None:
            raise HTTPException(409, "Selecciona un tema activo de tus materias asignadas")
        overlap = await db.scalar(
            select(AdvisingSession.id_asesoria)
            .where(
                AdvisingSession.id_docente == teacher_id,
                AdvisingSession.estado != "cancelada",
                AdvisingSession.inicio < data.fin,
                AdvisingSession.fin > data.inicio,
            )
            .limit(1)
        )
        if overlap:
            raise HTTPException(409, "El docente ya tiene una asesoría en ese horario")
        row = AdvisingSession(id_docente=teacher_id, **data.model_dump())
        db.add(row)
        await AcademicService.commit(db)
        return await repo.detail(db, row.id_asesoria, user)

    @staticmethod
    async def lock_session(db, id_):
        teacher_id = await db.scalar(
            select(AdvisingSession.id_docente).where(AdvisingSession.id_asesoria == id_)
        )
        if teacher_id is None:
            raise HTTPException(404, "Asesoría no encontrada")
        # Todos los cambios de agenda y cupo usan primero el mismo cerrojo de docente.
        await AdvisingService.lock_teacher(db, teacher_id)
        return await db.scalar(
            select(AdvisingSession)
            .where(AdvisingSession.id_asesoria == id_)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    @staticmethod
    def owner(user, row):
        if user.rol.nombre != "administrador" and (
            not user.docente or user.docente.id_docente != row.id_docente
        ):
            raise HTTPException(403, "Solo el docente responsable puede realizar esta operación")

    @staticmethod
    async def reserve(db, user, id_):
        row = await AdvisingService.lock_session(db, id_)
        student_id = user.estudiante.id_estudiante
        # Serializa también reservas del mismo estudiante con diferentes docentes.
        await db.scalar(select(Student).where(Student.id_estudiante == student_id).with_for_update())
        if row.estado != "programada" or utc(row.inicio) <= now_utc():
            raise HTTPException(409, "La asesoría ya no admite reservas")
        visible = await db.scalar(
            repo.query()
            .with_only_columns(AdvisingSession.id_asesoria)
            .where(AdvisingSession.id_asesoria == id_, *repo.visible_topic())
        )
        if visible is None:
            raise HTTPException(409, "La materia, tema o docente ya no están disponibles")
        participant = await db.scalar(
            select(Participant)
            .where(Participant.id_asesoria == id_, Participant.id_estudiante == student_id)
            .execution_options(populate_existing=True)
        )
        if participant and participant.estado == "reservada":
            return await repo.detail(db, id_, user)
        overlap = await db.scalar(
            select(Participant.id_participante)
            .join(AdvisingSession)
            .where(
                Participant.id_estudiante == student_id,
                Participant.estado == "reservada",
                AdvisingSession.estado == "programada",
                AdvisingSession.inicio < row.fin,
                AdvisingSession.fin > row.inicio,
            )
            .limit(1)
        )
        if overlap:
            raise HTTPException(409, "Ya tienes otra reserva en ese horario")
        occupied = await db.scalar(
            select(func.count())
            .select_from(Participant)
            .where(Participant.id_asesoria == id_, Participant.estado != "cancelada")
        )
        if occupied >= row.cupo_maximo:
            raise HTTPException(409, "La asesoría ya no tiene lugares disponibles")
        if participant:
            participant.estado = "reservada"
            participant.version += 1
        else:
            db.add(Participant(id_asesoria=id_, id_estudiante=student_id))
        await AcademicService.commit(db)
        return await repo.detail(db, id_, user)

    @staticmethod
    async def cancel_reservation(db, user, id_, data):
        row = await AdvisingService.lock_session(db, id_)
        participant = await db.scalar(
            select(Participant)
            .where(Participant.id_asesoria == id_, Participant.id_estudiante == user.estudiante.id_estudiante)
            .execution_options(populate_existing=True)
        )
        if participant is None:
            raise HTTPException(404, "Reserva no encontrada")
        AdvisingService.check_version(participant, data.version)
        if row.estado != "programada" or utc(row.inicio) <= now_utc() or participant.estado != "reservada":
            raise HTTPException(409, "Esta reserva ya no se puede cancelar")
        participant.estado = "cancelada"
        participant.version += 1
        await AcademicService.commit(db)
        return await repo.detail(db, id_, user)

    @staticmethod
    async def cancel_session(db, user, id_, data):
        row = await AdvisingService.lock_session(db, id_)
        AdvisingService.owner(user, row)
        AdvisingService.check_version(row, data.version)
        if row.estado != "programada" or utc(row.fin) <= now_utc():
            raise HTTPException(409, "Solo se puede cancelar una asesoría programada que no ha terminado")
        row.estado = "cancelada"
        row.motivo_cancelacion = data.motivo
        row.version += 1
        for p in (
            await db.scalars(
                select(Participant).where(Participant.id_asesoria == id_, Participant.estado == "reservada")
            )
        ).all():
            p.estado = "cancelada"
            p.version += 1
        await AcademicService.commit(db)
        return await repo.detail(db, id_, user)

    @staticmethod
    async def finalize(db, user, id_, data):
        row = await AdvisingService.lock_session(db, id_)
        AdvisingService.owner(user, row)
        AdvisingService.check_version(row, data.version)
        if row.estado != "programada" or utc(row.fin) > now_utc():
            raise HTTPException(409, "La asesoría solo se puede finalizar después de su hora de término")
        participants = (
            await db.scalars(
                select(Participant).where(Participant.id_asesoria == id_, Participant.estado == "reservada")
            )
        ).all()
        if not set(data.asistieron).issubset({p.id_estudiante for p in participants}):
            raise HTTPException(422, "La asistencia contiene estudiantes sin reserva activa")
        for p in participants:
            p.estado = "asistio" if p.id_estudiante in data.asistieron else "no_asistio"
            p.version += 1
        row.estado = "finalizada"
        row.version += 1
        await AcademicService.commit(db)
        return await repo.detail(db, id_, user)
