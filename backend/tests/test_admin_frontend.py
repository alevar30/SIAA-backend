import pytest
from sqlalchemy import update

from app.models.academic import Career
from app.models.user import User
from test_api import NEW_PASSWORD, PASSWORD, headers, login


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
    created = await client.post(
        "/api/v1/admin/estudiantes",
        headers=auth,
        json={"matricula": "TEST123"},
    )
    assert created.status_code == 201
    temporary = created.json()["password_temporal"]
    student = await login(client, "TEST123", temporary)
    student_auth = {"Authorization": "Bearer " + student.json()["access_token"]}
    response = await client.get("/api/v1/auth/primer-acceso/carreras", headers=student_auth)
    assert career_id in {career["id_carrera"] for career in response.json()}
    credentials = {
        "password_actual": temporary,
        "password_nueva": NEW_PASSWORD,
        "password_nueva_confirm": NEW_PASSWORD,
    }
    assert (
        await client.post("/api/v1/auth/cambiar-contrasena", headers=student_auth, json=credentials)
    ).status_code == 409
    assert (await client.get("/api/v1/admin/resumen", headers=student_auth)).status_code == 403
    response = await client.post(
        "/api/v1/auth/primer-acceso",
        headers=student_auth,
        json={
            **credentials,
            "nombre": " Ana ",
            "apellidos": " Pérez ",
            "id_carrera": career_id,
        },
    )
    assert response.status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=student_auth)).status_code == 401
    assert (await login(client, "TEST123", temporary)).status_code == 401
    result = await login(client, "TEST123", NEW_PASSWORD)
    assert result.json()["nombre"] == "Ana Pérez"
    ready_auth = {"Authorization": "Bearer " + result.json()["access_token"]}
    me = (await client.get("/api/v1/auth/me", headers=ready_auth)).json()
    assert me["requiere_completar_perfil"] is False
    assert me["carrera"] == "Gestión Empresarial"
    listed = await client.get("/api/v1/admin/usuarios", params={"q": "Ana Pérez"}, headers=auth)
    assert listed.json()["total"] == 1


async def test_reset_invalidates_old_credentials_without_erasing_student_profile(client, database):
    admin = await headers(client)
    student = await headers(client, "20260001")
    endpoint = "/api/v1/admin/usuarios/2/restablecer-contrasena"
    assert (await client.post(endpoint, headers=student)).status_code == 403
    assert (
        await client.post("/api/v1/admin/usuarios/999/restablecer-contrasena", headers=admin)
    ).status_code == 404
    reset = await client.post(endpoint, headers=admin)
    assert reset.status_code == 200 and reset.headers["cache-control"] == "no-store"
    assert set(reset.json()) == {"password_temporal"}
    temporary = reset.json()["password_temporal"]
    assert len(temporary) == 8
    assert (await client.get("/api/v1/auth/me", headers=student)).status_code == 401
    assert (await login(client, "20260001", PASSWORD)).status_code == 401
    result = await login(client, "20260001", temporary)
    assert result.status_code == 200
    auth = {"Authorization": "Bearer " + result.json()["access_token"]}
    profile = (await client.get("/api/v1/auth/me", headers=auth)).json()
    assert profile["debe_cambiar_contrasena"] is True
    assert profile["requiere_completar_perfil"] is False
    assert profile["carrera"] == "Sistemas"
    async with database() as db:
        await db.execute(update(User).where(User.id_usuario == 2).values(activo=False))
        await db.commit()
    assert (await client.post(endpoint, headers=admin)).status_code == 409


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
