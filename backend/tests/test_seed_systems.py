import pytest
from sqlalchemy import func, select

from app.models.academic import CareerSubject, Subject
from app.seed_systems import import_subjects, load_subjects
from test_api import headers


async def test_preview_then_import_is_repeatable_and_visible_in_api(database, client):
    async with database() as db:
        preview = await import_subjects(db)
        assert preview["materias_nuevas"] == 52
        assert not any(row.clave.startswith("CLE-") for row in load_subjects(1))
        assert await db.scalar(select(func.count()).select_from(Subject)) == 0
        await db.rollback()
        first = await import_subjects(db, apply=True)
        second = await import_subjects(db, apply=True)
        assert first["asociaciones_nuevas"] == 52
        assert second["materias_nuevas"] == second["asociaciones_nuevas"] == 0
        assert await db.scalar(select(func.count()).select_from(CareerSubject)) == 52
    response = await client.get(
        "/api/v1/catalogo/materias?id_carrera=1", headers=await headers(client, "20260001")
    )
    assert response.status_code == 200
    assert {row["clave"] for row in response.json()} == {row.clave for row in load_subjects(1)}


async def test_conflicting_existing_subject_aborts_entire_batch(database):
    async with database() as db:
        db.add(Subject(nombre="Otra materia", clave="IAC-2206", activo=True))
        await db.commit()
        with pytest.raises(ValueError, match="IAC-2206"):
            await import_subjects(db, apply=True)
        assert await db.scalar(select(func.count()).select_from(Subject)) == 1
        assert await db.scalar(select(func.count()).select_from(CareerSubject)) == 0


async def test_links_existing_subject_without_replacing_other_careers(database):
    from app.models.academic import Career

    async with database() as db:
        other = Career(nombre="Otra carrera", clave="OTRA")
        subject = Subject(nombre="Cálculo Diferencial", clave="ACF-0901", activo=True)
        db.add_all([other, subject])
        await db.flush()
        db.add(CareerSubject(id_carrera=other.id_carrera, id_materia=subject.id_materia))
        await db.commit()
        result = await import_subjects(db, apply=True)
        assert result["materias_nuevas"] == 51
        assert result["asociaciones_nuevas"] == 52
        await db.refresh(subject)
        assert subject.version == 2
        assert (
            len(
                (
                    await db.scalars(
                        select(CareerSubject).where(CareerSubject.id_materia == subject.id_materia)
                    )
                ).all()
            )
            == 2
        )
