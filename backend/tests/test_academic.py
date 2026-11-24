import asyncio
import os
import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.models.academic import Career, Subject, TeacherSubject, TeacherTopic, Topic
from app.models.user import User
from test_api import headers


async def make_subject(client, auth, name="Bases de Datos", key="SCD1022"):
    response = await client.post(
        "/api/v1/admin/catalogo/materias",
        headers=auth,
        json={"nombre": name, "clave": key, "carrera_ids": [1]},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def make_topic(client, auth, subject, name="Normalización"):
    response = await client.post(
        "/api/v1/admin/catalogo/temas",
        headers=auth,
        json={"id_materia": subject["id_materia"], "nombre": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def assign(client, auth, subject_ids, version=1):
    return await client.put(
        "/api/v1/admin/catalogo/docentes/1/materias",
        headers=auth,
        json={"materia_ids": subject_ids, "version": version},
    )


async def test_complete_catalog_assignment_and_search(client):
    admin = await headers(client)
    teacher = await headers(client, "EMP001")
    student = await headers(client, "20260001")
    subject = await make_subject(client, admin)
    topic = await make_topic(client, admin, subject)
    before = await client.get("/api/v1/docente/materias", headers=teacher)
    assert before.json()["materias"] == []
    response = await assign(client, admin, [subject["id_materia"]])
    assert response.status_code == 200, response.text
    version = response.json()["version"]
    response = await client.put(
        "/api/v1/docente/temas", headers=teacher, json={"tema_ids": [topic["id_tema"]], "version": version}
    )
    assert response.status_code == 200, response.text
    query = {"id_materia": subject["id_materia"], "id_tema": topic["id_tema"]}
    response = await client.get("/api/v1/catalogo/docentes", headers=student, params=query)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1 and body["items"][0]["nombre"] == "Docente"
    assert body["items"][0]["materias"][0]["tema_ids"] == [topic["id_tema"]]
    assert "password" not in response.text


async def test_removal_cascades_selected_topics_and_conflicts_with_stale_teacher(client, database):
    admin, teacher = await headers(client), await headers(client, "EMP001")
    subject = await make_subject(client, admin)
    topic = await make_topic(client, admin, subject)
    await assign(client, admin, [subject["id_materia"]])
    selected = await client.put(
        "/api/v1/docente/temas", headers=teacher, json={"tema_ids": [topic["id_tema"]], "version": 2}
    )
    version = selected.json()["version"]
    removed = await assign(client, admin, [], version)
    assert removed.status_code == 200
    stale = await client.put(
        "/api/v1/docente/temas", headers=teacher, json={"tema_ids": [topic["id_tema"]], "version": version}
    )
    assert stale.status_code == 409
    async with database() as db:
        assert (await db.scalars(select(TeacherTopic))).all() == []


async def test_teacher_cannot_select_unassigned_or_unknown_topics(client):
    admin, teacher = await headers(client), await headers(client, "EMP001")
    subject = await make_subject(client, admin)
    topic = await make_topic(client, admin, subject)
    for ids, code in [([topic["id_tema"]], 403), ([9999], 404), ([True], 422), ([1, 1], 422)]:
        response = await client.put(
            "/api/v1/docente/temas", headers=teacher, json={"tema_ids": ids, "version": 1}
        )
        assert response.status_code == code
    assert (await client.get("/api/v1/docente/materias", headers=teacher)).json()["version"] == 1


@pytest.mark.parametrize("identifier", ["EMP001", "20260001"])
async def test_catalog_admin_permissions(client, identifier):
    auth = await headers(client, identifier)
    assert (await client.get("/api/v1/admin/catalogo/materias", headers=auth)).status_code == 403
    assert (
        await client.post(
            "/api/v1/admin/catalogo/materias",
            headers=auth,
            json={"nombre": "Materia", "clave": "MAT01", "carrera_ids": [1]},
        )
    ).status_code == 403
    assert (await assign(client, auth, [])).status_code == 403


async def test_inactive_subject_preserves_assignments_and_disappears_from_search(client):
    admin, teacher, student = (
        await headers(client),
        await headers(client, "EMP001"),
        await headers(client, "20260001"),
    )
    subject = await make_subject(client, admin)
    topic = await make_topic(client, admin, subject)
    await assign(client, admin, [subject["id_materia"]])
    await client.put(
        "/api/v1/docente/temas", headers=teacher, json={"tema_ids": [topic["id_tema"]], "version": 2}
    )
    response = await client.put(
        f"/api/v1/admin/catalogo/materias/{subject['id_materia']}",
        headers=admin,
        json={
            "nombre": subject["nombre"],
            "clave": subject["clave"],
            "activo": False,
            "carrera_ids": [1],
            "version": subject["version"],
        },
    )
    assert response.status_code == 200
    assert (await client.get("/api/v1/catalogo/materias", headers=student)).json() == []
    own = (await client.get("/api/v1/docente/materias", headers=teacher)).json()
    assert own["materias"][0]["tema_ids"] == [topic["id_tema"]]
    assert own["materias"][0]["activo"] is False
    response = await client.put(
        "/api/v1/docente/temas", headers=teacher, json={"tema_ids": [], "version": own["version"]}
    )
    assert response.status_code == 200


async def test_topic_deactivation_and_mismatched_search(client):
    admin, teacher, student = (
        await headers(client),
        await headers(client, "EMP001"),
        await headers(client, "20260001"),
    )
    subject = await make_subject(client, admin)
    other = await make_subject(client, admin, "Programación", "PROG1")
    topic = await make_topic(client, admin, subject)
    wrong = await client.get(
        "/api/v1/catalogo/docentes",
        headers=student,
        params={"id_materia": other["id_materia"], "id_tema": topic["id_tema"]},
    )
    assert wrong.status_code == 422
    response = await client.put(
        f"/api/v1/admin/catalogo/temas/{topic['id_tema']}",
        headers=admin,
        json={"nombre": topic["nombre"], "activo": False, "version": topic["version"]},
    )
    assert response.status_code == 200
    await assign(client, admin, [subject["id_materia"]])
    assert (
        await client.put(
            "/api/v1/docente/temas", headers=teacher, json={"tema_ids": [topic["id_tema"]], "version": 2}
        )
    ).status_code == 409
    assert (
        await client.get(f"/api/v1/catalogo/materias/{subject['id_materia']}/temas", headers=student)
    ).json() == []


async def test_catalog_edits_duplicate_checks_and_optimistic_version(client):
    auth = await headers(client)
    subject = await make_subject(client, auth)
    duplicate = await client.post(
        "/api/v1/admin/catalogo/materias",
        headers=auth,
        json={"nombre": "Otra materia", "clave": "scd1022", "carrera_ids": [1]},
    )
    assert duplicate.status_code == 409
    body = {
        "nombre": "Bases de Datos II",
        "clave": subject["clave"],
        "carrera_ids": [1],
        "version": subject["version"],
    }
    assert (
        await client.put(f"/api/v1/admin/catalogo/materias/{subject['id_materia']}", headers=auth, json=body)
    ).status_code == 200
    assert (
        await client.put(f"/api/v1/admin/catalogo/materias/{subject['id_materia']}", headers=auth, json=body)
    ).status_code == 409
    topic = await make_topic(client, auth, subject)
    assert (
        await client.post(
            "/api/v1/admin/catalogo/temas",
            headers=auth,
            json={"nombre": " normalización ", "id_materia": subject["id_materia"]},
        )
    ).status_code == 409
    assert topic["id_tema"] > 0


async def test_career_edit_retains_existing_students(client, database):
    auth = await headers(client)
    subject = await make_subject(client, auth)
    career = (await client.get("/api/v1/admin/catalogo/carreras", headers=auth)).json()[0]
    body = {"nombre": "Sistemas actualizado", "clave": "ISC", "activo": False, "version": career["version"]}
    assert (await client.put("/api/v1/admin/catalogo/carreras/1", headers=auth, json=body)).status_code == 200
    assert (await client.put("/api/v1/admin/catalogo/carreras/1", headers=auth, json=body)).status_code == 409
    student = await headers(client, "20260001")
    assert (await client.get("/api/v1/auth/me", headers=student)).json()["carrera"] == "Sistemas actualizado"
    assert (await client.get("/api/v1/catalogo/materias", headers=student)).json() == []
    assert (await assign(client, auth, [subject["id_materia"]])).status_code == 409
    async with database() as db:
        assert await db.get(Career, 1) is not None


@pytest.mark.parametrize("ids,code", [([], 422), ([1, 1], 422), ([9999], 404), ([True], 422)])
async def test_subject_career_validation(client, ids, code):
    response = await client.post(
        "/api/v1/admin/catalogo/materias",
        headers=await headers(client),
        json={"nombre": "Materia válida", "clave": "MAT1", "carrera_ids": ids},
    )
    assert response.status_code == code


async def test_database_prevents_topic_outside_assigned_subject(database):
    async with database() as db:
        first = Subject(nombre="Primera materia", clave="ONE")
        second = Subject(nombre="Segunda materia", clave="TWO")
        db.add_all([first, second])
        await db.flush()
        topic = Topic(id_materia=second.id_materia, nombre="Tema de segunda")
        db.add_all([topic, TeacherSubject(id_docente=1, id_materia=first.id_materia)])
        await db.commit()
        db.add(TeacherTopic(id_docente=1, id_materia=first.id_materia, id_tema=topic.id_tema))
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()


async def test_public_requires_complete_profile_and_hides_disabled_teacher(client, database):
    admin, teacher, student = (
        await headers(client),
        await headers(client, "EMP001"),
        await headers(client, "20260001"),
    )
    subject = await make_subject(client, admin)
    topic = await make_topic(client, admin, subject)
    await assign(client, admin, [subject["id_materia"]])
    await client.put(
        "/api/v1/docente/temas", headers=teacher, json={"tema_ids": [topic["id_tema"]], "version": 2}
    )
    async with database() as db:
        await db.execute(update(User).where(User.id_usuario == 3).values(activo=False))
        await db.commit()
    result = await client.get(
        "/api/v1/catalogo/docentes",
        headers=student,
        params={"id_materia": subject["id_materia"], "id_tema": topic["id_tema"]},
    )
    assert result.json()["total"] == 0
    async with database() as db:
        await db.execute(update(User).where(User.id_usuario == 2).values(debe_cambiar_contrasena=True))
        await db.commit()
    assert (await client.get("/api/v1/catalogo/materias", headers=student)).status_code == 403


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Concurrencia verificada con PostgreSQL")
async def test_concurrent_admin_assignments_do_not_overwrite_each_other(client):
    admin = await headers(client)
    first = await make_subject(client, admin)
    second = await make_subject(client, admin, "Programación", "PROG2")
    results = await asyncio.gather(
        assign(client, admin, [first["id_materia"]]),
        assign(client, admin, [second["id_materia"]]),
    )
    assert sorted(response.status_code for response in results) == [200, 409]
    result = (await client.get("/api/v1/admin/catalogo/docentes/1", headers=admin)).json()
    assert result["version"] == 2 and len(result["materias"]) == 1


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Concurrencia verificada con PostgreSQL")
async def test_concurrent_removal_and_topic_selection_remain_consistent(client):
    admin, teacher = await headers(client), await headers(client, "EMP001")
    subject = await make_subject(client, admin)
    topic = await make_topic(client, admin, subject)
    await assign(client, admin, [subject["id_materia"]])
    results = await asyncio.gather(
        assign(client, admin, [], 2),
        client.put(
            "/api/v1/docente/temas", headers=teacher, json={"tema_ids": [topic["id_tema"]], "version": 2}
        ),
    )
    assert sorted(response.status_code for response in results) == [200, 409]
    result = (await client.get("/api/v1/docente/materias", headers=teacher)).json()
    assert result["version"] == 3
    if result["materias"]:
        assert result["materias"][0]["tema_ids"] == [topic["id_tema"]]


async def test_inactive_career_filter_excludes_shared_subject(client):
    admin, student = await headers(client), await headers(client, "20260001")
    career = (
        await client.post(
            "/api/v1/admin/carreras", headers=admin, json={"nombre": "Otra carrera", "clave": "OTR"}
        )
    ).json()
    response = await client.post(
        "/api/v1/admin/catalogo/materias",
        headers=admin,
        json={"nombre": "Materia compartida", "clave": "SHARED", "carrera_ids": [1, career["id_carrera"]]},
    )
    assert response.status_code == 201
    assert (
        await client.put(
            "/api/v1/admin/catalogo/carreras/1",
            headers=admin,
            json={"nombre": "Sistemas", "clave": "ISC", "activo": False, "version": 1},
        )
    ).status_code == 200
    assert (await client.get("/api/v1/catalogo/materias?id_carrera=1", headers=student)).json() == []
    assert (
        len(
            (
                await client.get(
                    "/api/v1/catalogo/materias", headers=student, params={"id_carrera": career["id_carrera"]}
                )
            ).json()
        )
        == 1
    )


async def test_metadata_edits_preserve_suspended_parent_state(client):
    admin = await headers(client)
    subject = await make_subject(client, admin)
    topic = await make_topic(client, admin, subject)
    await client.put(
        "/api/v1/admin/catalogo/carreras/1",
        headers=admin,
        json={"nombre": "Sistemas", "clave": "ISC", "activo": False, "version": 1},
    )
    response = await client.put(
        f"/api/v1/admin/catalogo/materias/{subject['id_materia']}",
        headers=admin,
        json={
            "nombre": "Materia con carrera suspendida",
            "clave": subject["clave"],
            "activo": True,
            "version": 1,
            "carrera_ids": [1],
        },
    )
    assert response.status_code == 200
    response = await client.put(
        f"/api/v1/admin/catalogo/materias/{subject['id_materia']}",
        headers=admin,
        json={
            "nombre": "Materia suspendida",
            "clave": subject["clave"],
            "activo": False,
            "version": 2,
            "carrera_ids": [1],
        },
    )
    assert response.status_code == 200
    response = await client.put(
        f"/api/v1/admin/catalogo/temas/{topic['id_tema']}",
        headers=admin,
        json={"nombre": "Tema actualizado", "activo": True, "version": 1},
    )
    assert response.status_code == 200
    response = await client.post(
        "/api/v1/admin/catalogo/temas",
        headers=admin,
        json={"nombre": "Nuevo tema activo", "id_materia": subject["id_materia"]},
    )
    assert response.status_code == 409
