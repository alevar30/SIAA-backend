from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import OperationalError

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.main import app
from app.models.academic import Career
from app.models.user import Role, User
from app.repositories.admin_repository import AdminRepository
from app.repositories.auth_repository import AuthRepository
from conftest import PASSWORD

STUDENT = {
    "nombre": "Nueva Estudiante",
    "correo": "new@example.com",
    "matricula": "20260002",
    "id_carrera": 1,
    "semestre": 2,
}
TEACHER = {
    "nombre": "Nuevo Docente",
    "correo": "newteacher@example.com",
    "numero_empleado": "EMP002",
    "departamento": "Sistemas",
}
NEW_PASSWORD = "OtraClaveSegura123!"


async def login(client, identifier="admin@example.com", password=PASSWORD):
    return await client.post("/api/v1/auth/login", json={"identificador": identifier, "password": password})


async def headers(client, identifier="admin@example.com"):
    response = await login(client, identifier)
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.mark.parametrize(
    "identifier,role",
    [
        ("admin@example.com", "administrador"),
        ("student@example.com", "estudiante"),
        ("20260001", "estudiante"),
        ("EMP001", "docente"),
        ("ADMIN@EXAMPLE.COM", "administrador"),
        ("  admin@example.com  ", "administrador"),
    ],
)
async def test_login_identifiers(client, identifier, role):
    response = await login(client, identifier)
    assert response.status_code == 200
    assert response.json()["rol"] == role
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "identifier,password",
    [
        ("absent@example.com", PASSWORD),
        ("admin@example.com", "incorrecta"),
    ],
)
async def test_invalid_credentials(client, identifier, password):
    response = await login(client, identifier, password)
    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciales inválidas"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("authorization", [None, "Bearer invalid", "Basic abc"])
async def test_missing_or_invalid_token(client, authorization):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": authorization} if authorization else {}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "payload",
    [
        {"sub": "no-entero", "ver": 1},
        {"sub": "0", "ver": 1},
        {"sub": "9" * 100, "ver": 1},
        {"sub": "1", "ver": True},
        {"sub": "1"},
        {"sub": "9999", "ver": 1},
        {"sub": "1", "ver": 999},
    ],
)
async def test_bad_token_claims(client, payload):
    token = create_access_token(payload)
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401


async def test_expired_token(client):
    token = create_access_token({"sub": "1", "ver": 1}, timedelta(seconds=-1))
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401


async def test_me_has_profile_without_secrets(client):
    response = await client.get("/api/v1/auth/me", headers=await headers(client, "20260001"))
    assert response.status_code == 200
    body = response.json()
    assert body["id_estudiante"] is not None and body["id_docente"] is None
    assert "password_hash" not in body and "token_version" not in body
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("target", ["user", "role"])
async def test_deactivation_applies_to_existing_token(client, database, target):
    auth = await headers(client)
    async with database() as db:
        if target == "user":
            await db.execute(update(User).where(User.correo == "admin@example.com").values(activo=False))
        else:
            await db.execute(update(Role).where(Role.nombre == "administrador").values(activo=False))
        await db.commit()
    assert (await client.get("/api/v1/auth/me", headers=auth)).status_code == 403
    assert (await login(client)).status_code == 403
    assert (await login(client, password="incorrecta")).status_code == 401


@pytest.mark.parametrize("identifier", ["20260001", "EMP001"])
async def test_non_admin_cannot_create_users(client, identifier):
    auth = await headers(client, identifier)
    for route, payload in [("estudiantes", STUDENT), ("docentes", TEACHER)]:
        assert (await client.post("/api/v1/admin/" + route, json=payload, headers=auth)).status_code == 403


async def test_mandatory_change_and_revocation_flow(client, database):
    old_auth = await headers(client)
    async with database() as db:
        await db.execute(
            update(User).where(User.correo == "admin@example.com").values(debe_cambiar_contrasena=True)
        )
        await db.commit()
    assert (await client.get("/api/v1/auth/me", headers=old_auth)).status_code == 200
    assert (await client.post("/api/v1/admin/estudiantes", headers=old_auth, json=STUDENT)).status_code == 403
    response = await client.post(
        "/api/v1/auth/cambiar-contrasena",
        headers=old_auth,
        json={
            "password_actual": PASSWORD,
            "password_nueva": NEW_PASSWORD,
            "password_nueva_confirm": NEW_PASSWORD,
        },
    )
    assert response.status_code == 200
    assert response.json()["requiere_nuevo_login"] is True
    assert (await client.get("/api/v1/auth/me", headers=old_auth)).status_code == 401
    assert (await login(client)).status_code == 401
    response = await login(client, password=NEW_PASSWORD)
    assert response.status_code == 200 and response.json()["debe_cambiar_contrasena"] is False
    auth = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert (await client.post("/api/v1/admin/estudiantes", headers=auth, json=STUDENT)).status_code == 201


@pytest.mark.parametrize(
    "current,new,confirm,code",
    [
        ("incorrecta", NEW_PASSWORD, NEW_PASSWORD, 400),
        (PASSWORD, NEW_PASSWORD, "DiferenteClave123!", 400),
        (PASSWORD, PASSWORD, PASSWORD, 400),
        (PASSWORD, "corta", "corta", 422),
        (PASSWORD, "ñ" * 37, "ñ" * 37, 422),
    ],
)
async def test_invalid_password_changes_leave_session_intact(client, current, new, confirm, code):
    auth = await headers(client)
    response = await client.post(
        "/api/v1/auth/cambiar-contrasena",
        headers=auth,
        json={
            "password_actual": current,
            "password_nueva": new,
            "password_nueva_confirm": confirm,
        },
    )
    assert response.status_code == code
    assert (await client.get("/api/v1/auth/me", headers=auth)).status_code == 200


async def test_optimistic_password_update_rejects_stale_session(database, password_hash):
    async with database() as first, database() as second:
        user1 = await AuthRepository.get_by_id(first, 1)
        user2 = await AuthRepository.get_by_id(second, 1)
        version = user2.token_version
        # Cerrar la lectura permite escribir en SQLite y mantiene el objeto obsoleto.
        await second.commit()
        assert await AuthRepository.update_password(first, user1, password_hash, version)
        assert not await AuthRepository.update_password(second, user2, password_hash, version)


@pytest.mark.parametrize(
    "route,payload,identifier",
    [
        ("estudiantes", STUDENT, "20260002"),
        ("docentes", TEACHER, "EMP002"),
    ],
)
async def test_create_user_random_password_and_profile(client, database, route, payload, identifier):
    response = await client.post("/api/v1/admin/" + route, headers=await headers(client), json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    temporary = body["password_temporal"]
    assert len(temporary) >= 24 and temporary != "SIAA-" + identifier
    assert "password_generica" not in body
    assert response.headers["cache-control"] == "no-store"
    async with database() as db:
        user = await db.get(User, body["id_usuario"])
        assert user.password_hash != temporary and verify_password(temporary, user.password_hash)
    response = await login(client, identifier, temporary)
    assert response.status_code == 200 and response.json()["debe_cambiar_contrasena"]
    auth = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert (await client.get("/api/v1/auth/me", headers=auth)).status_code == 200


async def test_duplicate_email_case_insensitive(client):
    payload = {**STUDENT, "correo": "ADMIN@EXAMPLE.COM"}
    response = await client.post("/api/v1/admin/estudiantes", json=payload, headers=await headers(client))
    assert response.status_code == 409


@pytest.mark.parametrize(
    "route,payload",
    [
        ("estudiantes", {**STUDENT, "matricula": "20260001"}),
        ("docentes", {**TEACHER, "numero_empleado": "EMP001"}),
    ],
)
async def test_duplicate_identifier(client, route, payload):
    assert (
        await client.post("/api/v1/admin/" + route, json=payload, headers=await headers(client))
    ).status_code == 409


async def test_missing_and_inactive_career(client, database):
    auth = await headers(client)
    response = await client.post(
        "/api/v1/admin/estudiantes", headers=auth, json={**STUDENT, "id_carrera": 999}
    )
    assert response.status_code == 404
    async with database() as db:
        await db.execute(update(Career).values(activo=False))
        await db.commit()
    assert (await client.post("/api/v1/admin/estudiantes", headers=auth, json=STUDENT)).status_code == 409
    async with database() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 3


async def test_database_conflict_rolls_back_orphan_user(client, database, monkeypatch):
    # La prevalidación no basta: simula un competidor que insertó la matrícula.
    monkeypatch.setattr(AdminRepository, "get_student_by_matricula", AsyncMock(return_value=None))
    response = await client.post(
        "/api/v1/admin/estudiantes", headers=await headers(client), json={**STUDENT, "matricula": "20260001"}
    )
    assert response.status_code == 409
    async with database() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 3
        assert await db.scalar(select(User).where(User.correo == STUDENT["correo"])) is None


async def test_database_email_index_handles_race(client, database, monkeypatch):
    monkeypatch.setattr(AdminRepository, "get_user_by_correo", AsyncMock(return_value=None))
    response = await client.post(
        "/api/v1/admin/estudiantes",
        headers=await headers(client),
        json={**STUDENT, "correo": "ADMIN@example.com"},
    )
    assert response.status_code == 409
    async with database() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 3


@pytest.mark.parametrize(
    "changes",
    [
        {"id_carrera": 0},
        {"id_carrera": 99999999999999},
        {"semestre": 13},
        {"nombre": "   "},
        {"correo": "incorrecto"},
        {"matricula": "invalida con espacios"},
    ],
)
async def test_input_validation(client, changes):
    response = await client.post(
        "/api/v1/admin/estudiantes", headers=await headers(client), json={**STUDENT, **changes}
    )
    assert response.status_code == 422


async def test_health_db_error_does_not_leak_details(client):
    async def broken_db():
        db = AsyncMock()
        db.execute.side_effect = OperationalError("secret-host password=private", {}, Exception("private"))
        yield db

    app.dependency_overrides[get_db] = broken_db
    response = await client.get("/health-db")
    assert response.status_code == 503
    assert response.json() == {"detail": "Base de datos no disponible"}
    assert "private" not in response.text
    assert (await client.get("/health")).status_code == 200


async def test_health_db_success(client):
    assert (await client.get("/health-db")).json()["status"] == "ok"


async def test_cors(client):
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_openapi_unique_routes_and_bearer():
    routes = [(tuple(sorted(route.methods)), route.path) for route in app.routes if hasattr(route, "methods")]
    assert len(routes) == len(set(routes))
    spec = app.openapi()
    assert spec["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert "application/json" in spec["paths"]["/api/v1/auth/login"]["post"]["requestBody"]["content"]


async def test_role_change_is_read_from_database(client, database):
    auth = await headers(client)
    async with database() as db:
        await db.execute(update(User).where(User.correo == "admin@example.com").values(id_rol=2))
        await db.commit()
    assert (await client.get("/api/v1/auth/me", headers=auth)).json()["rol"] == "estudiante"
    assert (await client.post("/api/v1/admin/estudiantes", headers=auth, json=STUDENT)).status_code == 403


async def test_ambiguous_legacy_identifier_is_rejected(client, database):
    from app.models.profiles import Teacher

    async with database() as db:
        await db.execute(update(Teacher).values(numero_empleado="20260001"))
        await db.commit()
    assert (await login(client, "20260001")).status_code == 401
    assert (await login(client, "student@example.com")).status_code == 200


async def test_raw_driver_error_health_is_sanitized(client):
    from asyncpg import InvalidPasswordError

    async def broken_db():
        db = AsyncMock()
        db.execute.side_effect = InvalidPasswordError("sensitive-server-details")
        yield db

    app.dependency_overrides[get_db] = broken_db
    response = await client.get("/health-db")
    assert response.status_code == 503
    assert "sensitive" not in response.text
