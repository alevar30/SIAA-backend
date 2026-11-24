from sqlalchemy import delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Career, CareerSubject, Subject, TeacherSubject, TeacherTopic, Topic
from app.models.profiles import Teacher
from app.models.user import Role, User
from app.schemas.academic import CareerRead, TopicRead


class AcademicRepository:
    @staticmethod
    async def careers(db: AsyncSession, active_only: bool = False):
        query = select(Career).order_by(Career.nombre, Career.id_carrera)
        if active_only:
            query = query.where(Career.activo.is_(True))
        return (await db.scalars(query)).all()

    @staticmethod
    def available_subject():
        return exists(
            select(CareerSubject.id_materia)
            .join(Career, Career.id_carrera == CareerSubject.id_carrera)
            .where(CareerSubject.id_materia == Subject.id_materia, Career.activo.is_(True))
        )

    @staticmethod
    async def subjects(db: AsyncSession, active_only: bool = False, career_id: int | None = None):
        query = select(Subject).order_by(Subject.nombre, Subject.id_materia)
        if active_only:
            query = query.where(Subject.activo.is_(True), AcademicRepository.available_subject())
        if career_id:
            membership = (
                select(CareerSubject.id_materia)
                .join(Career)
                .where(
                    CareerSubject.id_materia == Subject.id_materia,
                    CareerSubject.id_carrera == career_id,
                )
            )
            if active_only:
                membership = membership.where(Career.activo.is_(True))
            query = query.where(exists(membership))
        subjects = (await db.scalars(query)).all()
        return await AcademicRepository.subject_records(db, subjects)

    @staticmethod
    async def subject_records(db: AsyncSession, subjects):
        ids = [subject.id_materia for subject in subjects]
        careers_by_subject = {id_: [] for id_ in ids}
        if ids:
            rows = await db.execute(
                select(CareerSubject.id_materia, Career)
                .join(Career)
                .where(CareerSubject.id_materia.in_(ids))
                .order_by(Career.nombre, Career.id_carrera)
            )
            for subject_id, career in rows:
                careers_by_subject[subject_id].append(CareerRead.model_validate(career))
        return [
            {
                "id_materia": subject.id_materia,
                "nombre": subject.nombre,
                "clave": subject.clave,
                "activo": subject.activo,
                "version": subject.version,
                "carreras": careers_by_subject[subject.id_materia],
            }
            for subject in subjects
        ]

    @staticmethod
    async def topics(db: AsyncSession, subject_id: int, active_only: bool = False):
        query = select(Topic).where(Topic.id_materia == subject_id).order_by(Topic.nombre, Topic.id_tema)
        if active_only:
            query = query.join(Subject).where(
                Topic.activo.is_(True), Subject.activo.is_(True), AcademicRepository.available_subject()
            )
        return await AcademicRepository.topic_records(db, (await db.scalars(query)).all())

    @staticmethod
    async def topic_records(db: AsyncSession, topics):
        from app.models.advising import AdvisingSession

        ids = [topic.id_tema for topic in topics]
        used = (
            set(
                (
                    await db.scalars(
                        select(AdvisingSession.id_tema).where(AdvisingSession.id_tema.in_(ids)).distinct()
                    )
                ).all()
            )
            if ids
            else set()
        )
        creator_ids = {topic.id_creador for topic in topics if topic.id_creador is not None}
        creators = (
            {
                user.id_usuario: user.nombre_completo
                for user in (await db.scalars(select(User).where(User.id_usuario.in_(creator_ids)))).all()
            }
            if creator_ids
            else {}
        )
        return [
            TopicRead.model_validate(topic).model_copy(
                update={
                    "creador_nombre": creators.get(topic.id_creador),
                    "tiene_asesorias": topic.id_tema in used,
                }
            )
            for topic in topics
        ]

    @staticmethod
    async def teacher_row(db: AsyncSession, teacher_id: int, lock: bool = False):
        query = select(Teacher).where(Teacher.id_docente == teacher_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return await db.scalar(query)

    @staticmethod
    async def teacher_records(db: AsyncSession, teachers):
        teacher_ids = [teacher.id_docente for teacher in teachers]
        if not teacher_ids:
            return []
        users = {
            user.id_usuario: (user, role)
            for user, role in (
                await db.execute(
                    select(User, Role)
                    .join(Role)
                    .where(User.id_usuario.in_([teacher.id_usuario for teacher in teachers]))
                )
            ).all()
        }
        assignments = (
            (await db.execute(select(TeacherSubject).where(TeacherSubject.id_docente.in_(teacher_ids))))
            .scalars()
            .all()
        )
        subject_ids = sorted({row.id_materia for row in assignments})
        subjects = (
            await db.scalars(
                select(Subject)
                .where(Subject.id_materia.in_(subject_ids))
                .order_by(Subject.nombre, Subject.id_materia)
            )
        ).all()
        subject_records = {
            row["id_materia"]: row for row in await AcademicRepository.subject_records(db, subjects)
        }
        topics = (
            await db.scalars(
                select(Topic).where(Topic.id_materia.in_(subject_ids)).order_by(Topic.nombre, Topic.id_tema)
            )
        ).all()
        topics_by_subject = {id_: [] for id_ in subject_ids}
        for topic in await AcademicRepository.topic_records(db, topics):
            topics_by_subject[topic.id_materia].append(topic)
        selections = (
            await db.scalars(select(TeacherTopic).where(TeacherTopic.id_docente.in_(teacher_ids)))
        ).all()
        result = []
        for teacher in teachers:
            user, role = users[teacher.id_usuario]
            assigned_ids = {row.id_materia for row in assignments if row.id_docente == teacher.id_docente}
            records = []
            for subject in subjects:
                if subject.id_materia in assigned_ids:
                    records.append(
                        {
                            **subject_records[subject.id_materia],
                            "temas": topics_by_subject[subject.id_materia],
                            "tema_ids": sorted(
                                row.id_tema
                                for row in selections
                                if row.id_docente == teacher.id_docente
                                and row.id_materia == subject.id_materia
                            ),
                        }
                    )
            result.append(
                {
                    "id_docente": teacher.id_docente,
                    "id_usuario": user.id_usuario,
                    "nombre": user.nombre_completo,
                    "numero_empleado": teacher.numero_empleado,
                    "departamento": teacher.departamento,
                    "activo": user.activo and role.activo and role.nombre == "docente",
                    "version": teacher.academic_version,
                    "materias": records,
                }
            )
        return result

    @staticmethod
    async def teachers(
        db: AsyncSession,
        search: str,
        page: int,
        page_size: int,
        subject_id: int | None = None,
        topic_id: int | None = None,
        active_only: bool = False,
    ):
        query = select(Teacher).join(User).join(Role)
        if search:
            query = query.where(
                or_(
                    User.nombre.icontains(search, autoescape=True),
                    User.apellidos.icontains(search, autoescape=True),
                    Teacher.numero_empleado.icontains(search, autoescape=True),
                    Teacher.departamento.icontains(search, autoescape=True),
                )
            )
        if active_only:
            query = query.where(User.activo.is_(True), Role.activo.is_(True), Role.nombre == "docente")
        if subject_id:
            query = query.where(
                exists(
                    select(TeacherSubject.id_docente).where(
                        TeacherSubject.id_docente == Teacher.id_docente,
                        TeacherSubject.id_materia == subject_id,
                    )
                )
            )
        if topic_id:
            query = query.where(
                exists(
                    select(TeacherTopic.id_docente).where(
                        TeacherTopic.id_docente == Teacher.id_docente, TeacherTopic.id_tema == topic_id
                    )
                )
            )
        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        teachers = (
            await db.scalars(
                query.order_by(User.nombre, Teacher.id_docente)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return {
            "items": await AcademicRepository.teacher_records(db, teachers),
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def replace_careers(db: AsyncSession, subject_id: int, career_ids: list[int]):
        await db.execute(delete(CareerSubject).where(CareerSubject.id_materia == subject_id))
        db.add_all([CareerSubject(id_materia=subject_id, id_carrera=id_) for id_ in career_ids])
