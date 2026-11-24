import asyncio
from datetime import datetime, timedelta, timezone
import os

import pytest
from sqlalchemy import func, select

from app.models.academic import TeacherSubject, TeacherTopic, Topic
from app.models.advising import AdvisingSession, Availability, Participant
from app.models.profiles import Student, Teacher
from app.models.user import User
from test_academic import make_subject
from test_api import headers


def interval(hour=0, duration=60):
    start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(second=0, microsecond=0) + timedelta(
        hours=hour
    )
    return {"inicio": start.isoformat(), "fin": (start + timedelta(minutes=duration)).isoformat()}


async def setup(client, database, *, capacity=1, modality="presencial", hour=0):
    admin, teacher, student = (
        await headers(client),
        await headers(client, "EMP001"),
        await headers(client, "20260001"),
    )
    subject = await make_subject(client, admin)
    async with database() as db:
        topic = Topic(id_materia=subject["id_materia"], nombre="Tema de prueba", activo=True)
        db.add(topic)
        db.add(TeacherSubject(id_docente=1, id_materia=subject["id_materia"]))
        await db.flush()
        db.add(TeacherTopic(id_docente=1, id_tema=topic.id_tema, id_materia=subject["id_materia"]))
        await db.commit()
        topic_id = topic.id_tema
    response = await client.post(
        "/api/v1/docente/disponibilidades",
        headers=teacher,
        json={
            **interval(hour, 180),
            "modalidad": modality,
            "ubicacion": "https://example.com/reunion" if modality == "virtual" else "Aula 101",
        },
    )
    assert response.status_code == 201, response.text
    slot = response.json()
    data = {
        **interval(hour),
        "id_disponibilidad": slot["id_disponibilidad"],
        "id_tema": topic_id,
        "tipo": "individual" if capacity == 1 else "grupal",
        "cupo_maximo": capacity,
    }
    response = await client.post("/api/v1/docente/asesorias", headers=teacher, json=data)
    assert response.status_code == 201, response.text
    return admin, teacher, student, slot, response.json(), data


async def another_student(client, database, password_hash, number="20260003"):
    async with database() as db:
        user = User(
            id_rol=2,
            nombre="Otra estudiante",
            correo=f"{number}@example.com",
            password_hash=password_hash,
            activo=True,
            debe_cambiar_contrasena=False,
        )
        db.add(user)
        await db.flush()
        db.add(Student(id_usuario=user.id_usuario, id_carrera=1, matricula=number))
        await db.commit()
    return await headers(client, number)


async def test_full_booking_cancel_rebook_and_history(client, database):
    admin, teacher, student, slot, session, _ = await setup(client, database)
    path = f"/api/v1/asesorias/{session['id_asesoria']}"
    available = await client.get("/api/v1/asesorias/disponibles", headers=student)
    assert available.json()["total"] == 1
    booked = await client.post(path + "/reservar", headers=student)
    assert booked.status_code == 200, booked.text
    assert booked.json()["disponibles"] == 0
    assert booked.json()["participantes"] == []
    duplicate = await client.post(path + "/reservar", headers=student)
    assert duplicate.json()["mi_reserva"]["version"] == 1
    roster = await client.get(path, headers=teacher)
    assert roster.json()["participantes"][0]["matricula"] == "20260001"
    canceled = await client.put(path + "/cancelar-reserva", headers=student, json={"version": 1})
    assert canceled.status_code == 200
    assert canceled.json()["disponibles"] == 1
    history = await client.get("/api/v1/asesorias/mias?vista=historial", headers=student)
    assert history.json()["items"][0]["mi_reserva"]["estado"] == "cancelada"
    rebooked = await client.post(path + "/reservar", headers=student)
    assert rebooked.json()["mi_reserva"]["version"] == 3
    stale = await client.put(path + "/cancelar-reserva", headers=student, json={"version": 1})
    assert stale.status_code == 409
    cancel = await client.put(
        path + "/cancelar", headers=teacher, json={"version": 1, "motivo": "Reunión institucional"}
    )
    assert cancel.status_code == 200, cancel.text
    assert (await client.post(path + "/reservar", headers=student)).status_code == 409
    assert (await client.get("/api/v1/asesorias/disponibles", headers=student)).json()["total"] == 0
    history = (await client.get("/api/v1/asesorias/mias?vista=historial", headers=student)).json()
    assert history["items"][0]["motivo_cancelacion"] == "Reunión institucional"
    assert history["items"][0]["mi_reserva"]["estado"] == "cancelada"
    retired = await client.put(
        f"/api/v1/docente/disponibilidades/{slot['id_disponibilidad']}/cancelar",
        headers=teacher,
        json={"version": 1},
    )
    assert retired.status_code == 200


async def test_capacity_and_student_privacy(client, database, password_hash):
    _, teacher, student, _, session, _ = await setup(client, database)
    other = await another_student(client, database, password_hash)
    path = f"/api/v1/asesorias/{session['id_asesoria']}"
    await client.post(path + "/reservar", headers=student)
    assert (await client.post(path + "/reservar", headers=other)).status_code == 409
    detail = await client.get(path, headers=other)
    assert detail.json()["participantes"] == [] and detail.json()["mi_reserva"] is None
    assert "20260001" not in detail.text and "student@example.com" not in detail.text
    assert (
        await client.put(path + "/cancelar-reserva", headers=other, json={"version": 1})
    ).status_code == 404
    assert (
        await client.put(path + "/cancelar", headers=other, json={"version": 1, "motivo": "Sin permiso"})
    ).status_code == 403


@pytest.mark.parametrize(
    "change",
    [
        {"inicio": "2020-01-01T10:00:00Z", "fin": "2020-01-01T11:00:00Z"},
        {"inicio": "2030-01-01T10:00:00", "fin": "2030-01-01T11:00:00"},
        {"modalidad": "otro"},
        {"modalidad": "virtual", "ubicacion": "javascript:alert(1)"},
        {"modalidad": "virtual", "ubicacion": "https://user:password@example.com"},
        {"fin": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()},
    ],
)
async def test_availability_validation(client, change):
    teacher = await headers(client, "EMP001")
    response = await client.post(
        "/api/v1/docente/disponibilidades",
        headers=teacher,
        json={
            **interval(),
            "modalidad": "presencial",
            "ubicacion": "Aula 101",
            **change,
        },
    )
    assert response.status_code == 422


async def test_schedule_conflicts_and_slot_cannot_be_removed_with_sessions(client, database):
    _, teacher, _, slot, session, data = await setup(client, database)
    overlap = await client.post(
        "/api/v1/docente/disponibilidades",
        headers=teacher,
        json={**interval(1), "modalidad": "presencial", "ubicacion": "Aula 102"},
    )
    assert overlap.status_code == 409
    assert (await client.post("/api/v1/docente/asesorias", headers=teacher, json=data)).status_code == 409
    assert (
        await client.put(
            f"/api/v1/docente/disponibilidades/{slot['id_disponibilidad']}/cancelar",
            headers=teacher,
            json={"version": 1},
        )
    ).status_code == 409
    outside = await client.post("/api/v1/docente/asesorias", headers=teacher, json={**data, **interval(4)})
    assert outside.status_code == 409
    adjacent = await client.post("/api/v1/docente/asesorias", headers=teacher, json={**data, **interval(1)})
    assert adjacent.status_code == 201, adjacent.text
    unknown_topic = await client.post(
        "/api/v1/docente/asesorias", headers=teacher, json={**data, **interval(2), "id_tema": 9999}
    )
    assert unknown_topic.status_code == 409
    invalid_capacity = await client.post(
        "/api/v1/docente/asesorias", headers=teacher, json={**data, "cupo_maximo": 2}
    )
    assert invalid_capacity.status_code == 422


async def test_teacher_cannot_manage_another_teachers_schedule(client, database, password_hash):
    _, teacher, _, slot, session, data = await setup(client, database)
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
        db.add(Teacher(id_usuario=user.id_usuario, numero_empleado="EMP002"))
        await db.commit()
    other = await headers(client, "EMP002")
    assert (
        await client.put(
            f"/api/v1/docente/disponibilidades/{slot['id_disponibilidad']}/cancelar",
            headers=other,
            json={"version": 1},
        )
    ).status_code == 404
    assert (
        await client.post("/api/v1/docente/asesorias", headers=other, json={**data, **interval(1)})
    ).status_code == 404
    assert (
        await client.put(
            f"/api/v1/asesorias/{session['id_asesoria']}/cancelar",
            headers=other,
            json={"version": 1, "motivo": "Sin permiso"},
        )
    ).status_code == 403
    assert (await client.get("/api/v1/asesorias/mias", headers=other)).json()["total"] == 0


async def test_virtual_link_only_after_reservation_and_hidden_when_catalog_inactive(client, database):
    _, teacher, student, _, session, _ = await setup(client, database, modality="virtual")
    path = f"/api/v1/asesorias/{session['id_asesoria']}"
    assert "https://example.com/reunion" not in (await client.get(path, headers=student)).text
    booked = await client.post(path + "/reservar", headers=student)
    assert booked.json()["ubicacion"] == "https://example.com/reunion"
    async with database() as db:
        topic = await db.get(Topic, session["id_tema"])
        topic.activo = False
        await db.commit()
    assert (await client.get("/api/v1/asesorias/disponibles", headers=student)).json()["total"] == 0
    assert (await client.get("/api/v1/asesorias/mias", headers=student)).json()["total"] == 1
    assert (await client.get(path, headers=student)).status_code == 200


async def test_finalize_only_after_end_records_attendance(client, database, monkeypatch):
    _, teacher, student, _, session, _ = await setup(client, database)
    path = f"/api/v1/asesorias/{session['id_asesoria']}"
    await client.post(path + "/reservar", headers=student)
    assert (
        await client.put(path + "/finalizar", headers=teacher, json={"version": 1, "asistieron": [1]})
    ).status_code == 409
    future = datetime.fromisoformat(session["fin"].replace("Z", "+00:00")) + timedelta(minutes=1)
    monkeypatch.setattr("app.services.advising_service.now_utc", lambda: future)
    assert (
        await client.put(path + "/finalizar", headers=teacher, json={"version": 1, "asistieron": [9999]})
    ).status_code == 422
    done = await client.put(path + "/finalizar", headers=teacher, json={"version": 1, "asistieron": [1]})
    assert done.status_code == 200, done.text
    assert done.json()["estado"] == "finalizada"
    assert done.json()["participantes"][0]["estado"] == "asistio"
    assert (
        await client.put(path + "/finalizar", headers=teacher, json={"version": 1, "asistieron": []})
    ).status_code == 409
    assert (await client.get(path, headers=student)).json()["mi_reserva"]["estado"] == "asistio"


@pytest.mark.parametrize(
    "concurrent",
    [
        False,
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                not os.getenv("TEST_DATABASE_URL"), reason="Concurrencia requiere PostgreSQL"
            ),
        ),
    ],
)
async def test_student_overlap_between_different_teachers(client, database, password_hash, concurrent):
    _, teacher, student, slot, session, data = await setup(client, database)
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
        other = Teacher(id_usuario=user.id_usuario, numero_empleado="EMP002")
        db.add(other)
        await db.flush()
        availability = Availability(
            id_docente=other.id_docente,
            inicio=datetime.fromisoformat(data["inicio"]),
            fin=datetime.fromisoformat(data["fin"]),
            modalidad="presencial",
            ubicacion="Aula 102",
        )
        db.add(availability)
        await db.flush()
        db.add(TeacherSubject(id_docente=other.id_docente, id_materia=session["id_materia"]))
        await db.flush()
        db.add(
            TeacherTopic(
                id_docente=other.id_docente, id_tema=session["id_tema"], id_materia=session["id_materia"]
            )
        )
        second = AdvisingSession(
            id_docente=other.id_docente,
            id_disponibilidad=availability.id_disponibilidad,
            id_tema=session["id_tema"],
            inicio=availability.inicio,
            fin=availability.fin,
            tipo="individual",
            cupo_maximo=1,
        )
        db.add(second)
        await db.commit()
        second_id = second.id_asesoria
    if concurrent:
        results = await asyncio.gather(
            client.post(f"/api/v1/asesorias/{session['id_asesoria']}/reservar", headers=student),
            client.post(f"/api/v1/asesorias/{second_id}/reservar", headers=student),
        )
        assert sorted(r.status_code for r in results) == [200, 409]
    else:
        assert (
            await client.post(f"/api/v1/asesorias/{session['id_asesoria']}/reservar", headers=student)
        ).status_code == 200
        assert (
            await client.post(f"/api/v1/asesorias/{second_id}/reservar", headers=student)
        ).status_code == 409


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Concurrencia requiere PostgreSQL")
@pytest.mark.parametrize("capacity", [1, 2])
async def test_postgres_concurrent_last_place(client, database, password_hash, capacity):
    _, _, student, _, session, _ = await setup(client, database, capacity=capacity)
    other = await another_student(client, database, password_hash)
    path = f"/api/v1/asesorias/{session['id_asesoria']}/reservar"
    if capacity == 2:
        assert (await client.post(path, headers=student)).status_code == 200
        student = await another_student(client, database, password_hash, "20260004")
    results = await asyncio.gather(client.post(path, headers=student), client.post(path, headers=other))
    assert sorted(r.status_code for r in results) == [200, 409]
    async with database() as db:
        assert (
            await db.scalar(
                select(func.count()).select_from(Participant).where(Participant.estado == "reservada")
            )
            == capacity
        )


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Concurrencia requiere PostgreSQL")
async def test_postgres_concurrent_availability_and_session_overlap(client, database):
    teacher = await headers(client, "EMP001")
    data = {**interval(6), "modalidad": "presencial", "ubicacion": "Aula 105"}
    results = await asyncio.gather(
        *[client.post("/api/v1/docente/disponibilidades", headers=teacher, json=data) for _ in range(2)]
    )
    assert sorted(r.status_code for r in results) == [201, 409]
    _, teacher, _, _, _, session_data = await setup(client, database)
    new_session = {**session_data, **interval(1)}
    results = await asyncio.gather(
        *[client.post("/api/v1/docente/asesorias", headers=teacher, json=new_session) for _ in range(2)]
    )
    assert sorted(r.status_code for r in results) == [201, 409]


async def test_schedule_ids_and_pagination_are_bounded(client):
    student = await headers(client, "20260001")
    for url in [
        "/api/v1/asesorias/99999999999999999999999",
        "/api/v1/asesorias/disponibles?id_docente=99999999999999999999999",
        "/api/v1/asesorias/mias?page=99999999999999999999999",
    ]:
        assert (await client.get(url, headers=student)).status_code == 422
