import pytest
from sqlalchemy import update

from app.models.academic import Career
from app.models.user import User
from test_api import headers


async def test_user_list_profiles_and_no_secrets(client):
    response = await client.get("/api/v1/admin/usuarios?rol=estudiante", headers=await headers(client))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1 and body["page"] == 1
    assert body["items"][0]["matricula"] == "20260001"
    assert body["items"][0]["carrera"] == "Sistemas"
    assert "password" not in response.text and "token_version" not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("search,total", [("ADMIN", 1), ("20260001", 1), ("EMP001", 1), ("%", 0), ("_", 0)])
async def test_literal_user_search(client, search, total):
    response = await client.get("/api/v1/admin/usuarios", params={"q": search}, headers=await headers(client))
    assert response.status_code == 200
    assert response.json()["total"] == total


async def test_user_pagination_and_summary(client):
    auth = await headers(client)
    response = await client.get("/api/v1/admin/usuarios?page_size=1&page=2", headers=auth)
    assert response.status_code == 200
    assert response.json()["total"] == 3 and len(response.json()["items"]) == 1
    response = await client.get("/api/v1/admin/resumen", headers=auth)
    assert response.json() == {"estudiantes": 1, "docentes": 1, "administradores": 1, "carreras_activas": 1}


async def test_create_career_available_for_student_registration(client):
    auth = await headers(client)
    response = await client.post(
        "/api/v1/admin/carreras", headers=auth, json={"nombre": " Gestión Empresarial ", "clave": " ige "}
    )
    assert response.status_code == 201
    assert response.json()["clave"] == "IGE"
    assert response.json()["nombre"] == "Gestión Empresarial"
    career_id = response.json()["id_carrera"]
    response = await client.post(
        "/api/v1/admin/estudiantes",
        headers=auth,
        json={
            "nombre": "Ana Estudiante",
            "correo": "ana@example.com",
            "matricula": "TEST123",
            "id_carrera": career_id,
            "semestre": 3,
        },
    )
    assert response.status_code == 201
    assert "password_temporal" in response.json()


async def test_duplicate_and_invalid_career(client):
    auth = await headers(client)
    assert (
        await client.post(
            "/api/v1/admin/carreras", headers=auth, json={"nombre": "Otra carrera", "clave": "isc"}
        )
    ).status_code == 409
    assert (
        await client.post("/api/v1/admin/carreras", headers=auth, json={"nombre": "  ", "clave": "a b"})
    ).status_code == 422


async def test_careers_filter_inactive(client, database):
    auth = await headers(client)
    async with database() as db:
        await db.execute(update(Career).values(activo=False))
        await db.commit()
    assert (await client.get("/api/v1/admin/carreras", headers=auth)).json() == []
    response = await client.get("/api/v1/admin/carreras?active_only=false", headers=auth)
    assert len(response.json()) == 1


@pytest.mark.parametrize("identifier", ["20260001", "EMP001"])
async def test_new_admin_endpoints_forbid_other_roles(client, identifier):
    auth = await headers(client, identifier)
    for path in ("usuarios", "carreras", "resumen"):
        assert (await client.get("/api/v1/admin/" + path, headers=auth)).status_code == 403
    assert (
        await client.post("/api/v1/admin/carreras", headers=auth, json={"nombre": "Carrera", "clave": "XX"})
    ).status_code == 403


async def test_new_endpoints_require_password_change(client, database):
    auth = await headers(client)
    async with database() as db:
        await db.execute(
            update(User).where(User.correo == "admin@example.com").values(debe_cambiar_contrasena=True)
        )
        await db.commit()
    assert (await client.get("/api/v1/admin/usuarios", headers=auth)).status_code == 403


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "rol=root"])
async def test_user_filters_validate(client, query):
    assert (
        await client.get("/api/v1/admin/usuarios?" + query, headers=await headers(client))
    ).status_code == 422
