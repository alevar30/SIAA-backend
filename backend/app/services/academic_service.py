from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Career, CareerSubject, Subject, TeacherSubject, TeacherTopic, Topic
from app.models.profiles import Teacher
from app.repositories.academic_repository import AcademicRepository as repo


class AcademicService:
    @staticmethod
    async def commit(db: AsyncSession):
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(
                409,
                "Los datos cambiaron o ya existe un registro con esa clave. Recarga e inténtalo de nuevo.",
            ) from exc

    @staticmethod
    async def check_version(db: AsyncSession, model, id_column, id_: int, version: int):
        record = await db.scalar(
            select(model).where(id_column == id_).with_for_update().execution_options(populate_existing=True)
        )
        if record is None:
            raise HTTPException(404, "Registro no encontrado")
        if record.version != version:
            raise HTTPException(409, "El registro cambió desde que lo abriste. Recarga antes de guardar.")
        return record

    @staticmethod
    async def update_career(db: AsyncSession, id_: int, data):
        career = await AcademicService.check_version(db, Career, Career.id_carrera, id_, data.version)
        duplicate = await db.scalar(
            select(Career.id_carrera).where(func.upper(Career.clave) == data.clave, Career.id_carrera != id_)
        )
        if duplicate:
            raise HTTPException(409, "Ya existe una carrera con esa clave")
        changed = await db.execute(
            update(Career)
            .where(Career.id_carrera == id_, Career.version == data.version)
            .values(nombre=data.nombre, clave=data.clave, activo=data.activo, version=Career.version + 1)
            .execution_options(synchronize_session=False)
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "El registro cambió. Recarga antes de guardar.")
        await AcademicService.commit(db)
        await db.refresh(career)
        return career

    @staticmethod
    async def write_subject(db: AsyncSession, data, id_: int | None = None):
        subject = None
        if id_ is not None:
            subject = await AcademicService.check_version(db, Subject, Subject.id_materia, id_, data.version)
        duplicate = await db.scalar(
            select(Subject.id_materia).where(
                func.upper(Subject.clave) == data.clave, Subject.id_materia != (id_ or 0)
            )
        )
        if duplicate:
            raise HTTPException(409, "Ya existe una materia con esa clave")
        careers = (
            await db.scalars(
                select(Career)
                .where(Career.id_carrera.in_(data.carrera_ids))
                .order_by(Career.id_carrera)
                .with_for_update()
            )
        ).all()
        if len(careers) != len(data.carrera_ids):
            raise HTTPException(404, "Una de las carreras seleccionadas no existe")
        old_ids = set()
        if id_:
            old_ids = set(
                (
                    await db.scalars(select(CareerSubject.id_carrera).where(CareerSubject.id_materia == id_))
                ).all()
            )
        if any(not career.activo and career.id_carrera not in old_ids for career in careers):
            raise HTTPException(409, "Solo puedes agregar carreras activas")
        if (
            data.activo
            and not any(career.activo for career in careers)
            and (subject is None or not subject.activo)
        ):
            raise HTTPException(409, "Una materia activa necesita al menos una carrera activa")
        if subject is None:
            subject = Subject(nombre=data.nombre, clave=data.clave, activo=data.activo)
            db.add(subject)
            try:
                await db.flush()
            except IntegrityError as exc:
                await db.rollback()
                raise HTTPException(409, "Ya existe una materia con esa clave") from exc
        else:
            result = await db.execute(
                update(Subject)
                .where(Subject.id_materia == id_, Subject.version == data.version)
                .values(nombre=data.nombre, clave=data.clave, activo=data.activo, version=Subject.version + 1)
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise HTTPException(409, "El registro cambió. Recarga antes de guardar.")
        await repo.replace_careers(db, subject.id_materia, data.carrera_ids)
        await AcademicService.commit(db)
        await db.refresh(subject)
        return (await repo.subject_records(db, [subject]))[0]

    @staticmethod
    async def write_topic(db: AsyncSession, data, id_: int | None = None, *, user):
        topic = await db.get(Topic, id_) if id_ else None
        if id_ and topic is None:
            raise HTTPException(404, "Tema no encontrado")
        subject_id = topic.id_materia if topic else data.id_materia
        is_teacher = user.rol.nombre == "docente"
        if is_teacher:
            if user.docente is None:
                raise HTTPException(404, "Perfil docente no encontrado")
            # Mismo orden de bloqueo que asignaciones: docente, materia y tema.
            await repo.teacher_row(db, user.docente.id_docente, lock=True)
            assigned = await db.scalar(
                select(TeacherSubject.id_materia).where(
                    TeacherSubject.id_docente == user.docente.id_docente,
                    TeacherSubject.id_materia == subject_id,
                )
            )
            if assigned is None:
                raise HTTPException(403, "Solo puedes gestionar temas de tus materias asignadas")
        subject = await db.scalar(
            select(Subject)
            .where(Subject.id_materia == subject_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if subject is None:
            raise HTTPException(404, "Materia no encontrada")
        if topic is not None:
            topic = await AcademicService.check_version(db, Topic, Topic.id_tema, id_, data.version)
            if is_teacher and topic.id_creador != user.id_usuario:
                raise HTTPException(
                    403, "Solo puedes editar los temas que creaste; solicita otros cambios a administración"
                )
            from app.models.advising import AdvisingSession

            if (topic.nombre != data.nombre or topic.descripcion != data.descripcion) and await db.scalar(
                select(AdvisingSession.id_asesoria).where(AdvisingSession.id_tema == id_).limit(1)
            ):
                raise HTTPException(
                    409,
                    "Este tema ya tiene asesorías. Conserva su contenido y cambia únicamente su estado; crea otro tema si lo necesitas.",
                )
        if is_teacher and (topic is None or (data.activo and not topic.activo)):
            if not subject.activo or not await db.scalar(
                select(Subject.id_materia).where(Subject.id_materia == subject_id, repo.available_subject())
            ):
                raise HTTPException(409, "Solo puedes crear o activar temas de materias y carreras activas")
        if data.activo and not subject.activo and (topic is None or not topic.activo):
            raise HTTPException(409, "Activa la materia antes de activar o crear sus temas")
        duplicate = await db.scalar(
            select(Topic.id_tema).where(
                Topic.id_materia == subject_id,
                func.lower(func.trim(Topic.nombre)) == data.nombre.lower(),
                Topic.id_tema != (id_ or 0),
            )
        )
        if duplicate:
            raise HTTPException(409, "Ya existe un tema con ese nombre en esta materia")
        if topic is None:
            topic = Topic(
                id_materia=subject_id,
                nombre=data.nombre,
                descripcion=data.descripcion,
                activo=data.activo,
                id_creador=user.id_usuario,
            )
            db.add(topic)
        else:
            result = await db.execute(
                update(Topic)
                .where(Topic.id_tema == id_, Topic.version == data.version)
                .values(
                    nombre=data.nombre,
                    descripcion=data.descripcion,
                    activo=data.activo,
                    version=Topic.version + 1,
                )
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise HTTPException(409, "El tema cambió. Recarga antes de guardar.")
        await AcademicService.commit(db)
        await db.refresh(topic)
        return (await repo.topic_records(db, [topic]))[0]

    @staticmethod
    async def teacher(db: AsyncSession, id_: int):
        teacher = await repo.teacher_row(db, id_)
        if teacher is None:
            raise HTTPException(404, "Docente no encontrado")
        return (await repo.teacher_records(db, [teacher]))[0]

    @staticmethod
    async def advance_teacher(db: AsyncSession, teacher, expected: int):
        result = await db.execute(
            update(Teacher)
            .where(Teacher.id_docente == teacher.id_docente, Teacher.academic_version == expected)
            .values(academic_version=Teacher.academic_version + 1)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise HTTPException(409, "Las asignaciones cambiaron. Recarga antes de guardar.")

    @staticmethod
    async def assign_subjects(db: AsyncSession, id_: int, data):
        teacher = await repo.teacher_row(db, id_, lock=True)
        if teacher is None:
            raise HTTPException(404, "Docente no encontrado")
        if teacher.academic_version != data.version:
            raise HTTPException(409, "Las asignaciones cambiaron. Recarga antes de guardar.")
        if not (await repo.teacher_records(db, [teacher]))[0]["activo"]:
            raise HTTPException(409, "El docente está desactivado o no tiene el rol docente")
        old_ids = set(
            (
                await db.scalars(select(TeacherSubject.id_materia).where(TeacherSubject.id_docente == id_))
            ).all()
        )
        new_ids = set(data.materia_ids)
        subjects = (
            await db.scalars(
                select(Subject)
                .where(Subject.id_materia.in_(new_ids))
                .order_by(Subject.id_materia)
                .with_for_update()
            )
        ).all()
        if len(subjects) != len(new_ids):
            raise HTTPException(404, "Una de las materias no existe")
        available = {row["id_materia"] for row in await repo.subjects(db, active_only=True)}
        if new_ids - old_ids - available:
            raise HTTPException(409, "Solo puedes agregar materias activas vinculadas a una carrera activa")
        await AcademicService.advance_teacher(db, teacher, data.version)
        # El FK compuesto elimina las selecciones del docente para materias retiradas.
        removed = old_ids - new_ids
        if removed:
            await db.execute(
                delete(TeacherSubject).where(
                    TeacherSubject.id_docente == id_, TeacherSubject.id_materia.in_(removed)
                )
            )
        db.add_all(
            [
                TeacherSubject(id_docente=id_, id_materia=subject_id)
                for subject_id in sorted(new_ids - old_ids)
            ]
        )
        await AcademicService.commit(db)
        await db.refresh(teacher)
        return await AcademicService.teacher(db, id_)

    @staticmethod
    async def select_topics(db: AsyncSession, teacher_id: int, data):
        teacher = await repo.teacher_row(db, teacher_id, lock=True)
        if teacher is None:
            raise HTTPException(404, "Perfil docente no encontrado")
        if teacher.academic_version != data.version:
            raise HTTPException(409, "Las asignaciones cambiaron. Recarga antes de guardar.")
        assigned = set(
            (
                await db.scalars(
                    select(TeacherSubject.id_materia).where(TeacherSubject.id_docente == teacher_id)
                )
            ).all()
        )
        await db.scalars(
            select(Subject)
            .where(Subject.id_materia.in_(assigned))
            .order_by(Subject.id_materia)
            .with_for_update()
        )
        topics = (await db.scalars(select(Topic).where(Topic.id_tema.in_(data.tema_ids)))).all()
        if len(topics) != len(data.tema_ids):
            raise HTTPException(404, "Uno de los temas no existe")
        previous = set(
            (
                await db.scalars(select(TeacherTopic.id_tema).where(TeacherTopic.id_docente == teacher_id))
            ).all()
        )
        available = {row["id_materia"] for row in await repo.subjects(db, active_only=True)}
        for topic in topics:
            if topic.id_materia not in assigned:
                raise HTTPException(403, "Solo puedes seleccionar temas de tus materias asignadas")
            if topic.id_tema not in previous and (not topic.activo or topic.id_materia not in available):
                raise HTTPException(409, "Solo puedes agregar temas activos de materias disponibles")
        await AcademicService.advance_teacher(db, teacher, data.version)
        await db.execute(delete(TeacherTopic).where(TeacherTopic.id_docente == teacher_id))
        db.add_all(
            [
                TeacherTopic(id_docente=teacher_id, id_tema=topic.id_tema, id_materia=topic.id_materia)
                for topic in topics
            ]
        )
        await AcademicService.commit(db)
        await db.refresh(teacher)
        return await AcademicService.teacher(db, teacher_id)

    @staticmethod
    async def search_teachers(db: AsyncSession, subject_id: int, topic_id: int, page: int, page_size: int):
        subjects = await repo.subjects(db, active_only=True)
        if subject_id not in {row["id_materia"] for row in subjects}:
            raise HTTPException(404, "Materia no disponible")
        topic = await db.get(Topic, topic_id)
        if topic is None or not topic.activo:
            raise HTTPException(404, "Tema no disponible")
        if topic.id_materia != subject_id:
            raise HTTPException(422, "El tema no pertenece a la materia seleccionada")
        result = await repo.teachers(db, "", page, page_size, subject_id, topic_id, active_only=True)
        # La consulta pública expone únicamente la oferta activa del docente.
        for teacher in result["items"]:
            teacher["materias"] = [
                subject for subject in teacher["materias"] if subject["id_materia"] == subject_id
            ]
            for subject in teacher["materias"]:
                subject["temas"] = [
                    topic
                    for topic in subject["temas"]
                    if topic.activo and topic.id_tema in subject["tema_ids"]
                ]
                subject["tema_ids"] = [topic.id_tema for topic in subject["temas"]]
        return result
