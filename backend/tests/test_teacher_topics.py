import asyncio
import os

import pytest
from sqlalchemy import func, select

from app.models.academic import TeacherSubject, Topic
from app.models.profiles import Teacher
from app.models.user import User
from test_academic import assign, make_subject
from test_advising import setup as advising_setup
from test_api import headers


async def assigned_subject(client):
    admin, teacher = await headers(client), await headers(client, "EMP001")
    subject = await make_subject(client, admin)
    assert (await assign(client, admin, [subject["id_materia"]])).status_code == 200
    return admin, teacher, subject


async def second_teacher(client, database, password_hash, subject_id):
    async with database() as db:
        user = User(
            id_rol=3,
            nombre="Otro docente",
            correo="otro@example.com",
            password_hash=password_hash,
            debe_cambiar_contrasena=False,
        )
        db.add(user)
        await db.flush()
        teacher = Teacher(id_usuario=user.id_usuario, numero_empleado="EMP002")
        db.add(teacher)
        await db.flush()
        db.add(TeacherSubject(id_docente=teacher.id_docente, id_materia=subject_id))
        await db.commit()
    return await headers(client, "EMP002")


def edit(topic, **changes):
    return dict(
        nombre=topic["nombre"],
        descripcion=topic["descripcion"],
        activo=topic["activo"],
        version=topic["version"],
        **changes,
    )


async def test_teacher_creates_owns_and_edits_topic_while_others_can_select(client, database, password_hash):
    admin, teacher, subject = await assigned_subject(client)
    response = await client.post(
        "/api/v1/docente/temas",
        headers=teacher,
        json={"id_materia": subject["id_materia"], "nombre": "Normalización"},
    )
    assert response.status_code == 201, response.text
    topic = response.json()
    assert topic["id_creador"] == 3 and topic["creador_nombre"] == "Docente"
    assert not topic["tiene_asesorias"]
    own = (await client.get("/api/v1/docente/materias", headers=teacher)).json()
    assert own["materias"][0]["temas"][0]["id_creador"] == 3
    assert own["materias"][0]["tema_ids"] == []
    change = {**edit(topic), "nombre": "Formas normales"}
    edited = await client.put(f"/api/v1/docente/temas/{topic['id_tema']}", headers=teacher, json=change)
    assert edited.status_code == 200
    topic = edited.json()
    assert topic["version"] == 2
    assert (
        await client.put(f"/api/v1/docente/temas/{topic['id_tema']}", headers=teacher, json=change)
    ).status_code == 409
    other = await second_teacher(client, database, password_hash, subject["id_materia"])
    shared = (await client.get("/api/v1/docente/materias", headers=other)).json()
    assert shared["materias"][0]["temas"][0]["nombre"] == "Formas normales"
    assert (
        await client.put(f"/api/v1/docente/temas/{topic['id_tema']}", headers=other, json=edit(topic))
    ).status_code == 403
    select = await client.put(
        "/api/v1/docente/temas",
        headers=other,
        json={"tema_ids": [topic["id_tema"]], "version": shared["version"]},
    )
    assert select.status_code == 200
    updated = await client.put(
        f"/api/v1/admin/catalogo/temas/{topic['id_tema']}",
        headers=admin,
        json={**edit(topic), "activo": False},
    )
    assert updated.status_code == 200 and updated.json()["id_creador"] == 3


async def test_unassigned_subject_and_removed_assignment_prevent_management(client):
    admin, teacher = await headers(client), await headers(client, "EMP001")
    subject = await make_subject(client, admin)
    payload = {"id_materia": subject["id_materia"], "nombre": "Sin permiso"}
    assert (await client.post("/api/v1/docente/temas", headers=teacher, json=payload)).status_code == 403
    await assign(client, admin, [subject["id_materia"]])
    topic = (await client.post("/api/v1/docente/temas", headers=teacher, json=payload)).json()
    await assign(client, admin, [], 2)
    assert (
        await client.put(f"/api/v1/docente/temas/{topic['id_tema']}", headers=teacher, json=edit(topic))
    ).status_code == 403
    assert (await client.post("/api/v1/docente/temas", headers=teacher, json=payload)).status_code == 403


@pytest.mark.parametrize("identifier", ["admin@example.com", "20260001"])
async def test_teacher_endpoints_reject_other_roles(client, identifier):
    auth = await headers(client, identifier)
    assert (
        await client.post("/api/v1/docente/temas", headers=auth, json={"id_materia": 1, "nombre": "Tema"})
    ).status_code == 403
    assert (
        await client.put("/api/v1/docente/temas/1", headers=auth, json={"nombre": "Tema", "version": 1})
    ).status_code == 403


async def test_cannot_forge_author_move_topic_or_claim_legacy_topic(client, database):
    _, teacher, subject = await assigned_subject(client)
    assert (
        await client.post(
            "/api/v1/docente/temas",
            headers=teacher,
            json={"id_materia": subject["id_materia"], "nombre": "Falso autor", "id_creador": 1},
        )
    ).status_code == 422
    async with database() as db:
        legacy = Topic(id_materia=subject["id_materia"], nombre="Tema anterior")
        db.add(legacy)
        await db.commit()
        id_ = legacy.id_tema
    assert (
        await client.put(
            f"/api/v1/docente/temas/{id_}", headers=teacher, json={"nombre": "Tema anterior", "version": 1}
        )
    ).status_code == 403
    assert (
        await client.put(
            f"/api/v1/docente/temas/{id_}",
            headers=teacher,
            json={"nombre": "Tema anterior", "version": 1, "id_materia": 2},
        )
    ).status_code == 422


async def test_duplicate_and_suspended_subject_rules(client):
    admin, teacher, subject = await assigned_subject(client)
    payload = {"id_materia": subject["id_materia"], "nombre": "Tema compartido"}
    assert (await client.post("/api/v1/docente/temas", headers=teacher, json=payload)).status_code == 201
    assert (
        await client.post(
            "/api/v1/docente/temas", headers=teacher, json={**payload, "nombre": " TEMA COMPARTIDO "}
        )
    ).status_code == 409
    await client.put(
        "/api/v1/admin/catalogo/carreras/1",
        headers=admin,
        json={"nombre": "Sistemas", "clave": "ISC", "activo": False, "version": 1},
    )
    assert (
        await client.post("/api/v1/docente/temas", headers=teacher, json={**payload, "nombre": "Tema nuevo"})
    ).status_code == 409


async def test_topic_with_sessions_preserves_content_and_allows_deactivation(client, database):
    admin, teacher, _, _, session, _ = await advising_setup(client, database)
    async with database() as db:
        topic = await db.get(Topic, session["id_tema"])
        topic.id_creador = 3
        await db.commit()
    topics = (
        await client.get(f"/api/v1/admin/catalogo/materias/{session['id_materia']}/temas", headers=admin)
    ).json()
    topic = topics[0]
    assert topic["tiene_asesorias"]
    for route, auth in [("docente", teacher), ("admin/catalogo", admin)]:
        assert (
            await client.put(
                f"/api/v1/{route}/temas/{topic['id_tema']}",
                headers=auth,
                json={**edit(topic), "nombre": "Contenido distinto"},
            )
        ).status_code == 409
        assert (
            await client.put(
                f"/api/v1/{route}/temas/{topic['id_tema']}",
                headers=auth,
                json={**edit(topic), "descripcion": "Otra descripción"},
            )
        ).status_code == 409
    result = await client.put(
        f"/api/v1/docente/temas/{topic['id_tema']}", headers=teacher, json={**edit(topic), "activo": False}
    )
    assert result.status_code == 200
    detail = await client.get(f"/api/v1/asesorias/{session['id_asesoria']}", headers=teacher)
    assert detail.json()["tema"] == topic["nombre"]


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Concurrencia requiere PostgreSQL")
async def test_postgres_two_teachers_cannot_create_duplicate_topic(client, database, password_hash):
    _, teacher, subject = await assigned_subject(client)
    other = await second_teacher(client, database, password_hash, subject["id_materia"])
    payload = {"id_materia": subject["id_materia"], "nombre": "Un único tema"}
    results = await asyncio.gather(
        client.post("/api/v1/docente/temas", headers=teacher, json=payload),
        client.post("/api/v1/docente/temas", headers=other, json=payload),
    )
    assert sorted(r.status_code for r in results) == [201, 409]
    async with database() as db:
        assert await db.scalar(select(func.count()).select_from(Topic)) == 1
