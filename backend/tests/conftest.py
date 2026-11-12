import os
from pathlib import Path
import secrets

# Nunca cargar credenciales locales ni reutilizar la base de la aplicación.
os.environ.update(
    {
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_SERVER": "127.0.0.1",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "siaa_test",
        "SECRET_KEY": "test-only-9d710685c28143d6bfac1ae7790fa948",
        "SQL_ECHO": "false",
    }
)

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import BigInteger, event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import Career
from app.models.profiles import Student, Teacher
from app.models.user import Role, User

PASSWORD = "ClaveInicial123!"


@compiles(BigInteger, "sqlite")
def sqlite_bigint(element, compiler, **kwargs):
    # PostgreSQL usa BIGSERIAL; SQLite exige INTEGER para autoincrementar una PK.
    return "INTEGER"


@pytest.fixture(scope="session")
def password_hash():
    return get_password_hash(PASSWORD)


@pytest_asyncio.fixture
async def database(tmp_path: Path, password_hash):
    postgres_url = os.getenv("TEST_DATABASE_URL")
    owner = None
    schema = None
    if postgres_url:
        if not postgres_url.startswith("postgresql+asyncpg://"):
            raise ValueError("TEST_DATABASE_URL debe usar postgresql+asyncpg://")
        schema = "siaa_test_" + secrets.token_hex(8)
        owner = create_async_engine(postgres_url)
        async with owner.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(postgres_url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine("sqlite+aiosqlite:///" + (tmp_path / "test.db").as_posix())

        @event.listens_for(engine.sync_engine, "connect")
        def foreign_keys(dbapi_connection, connection_record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            db.add_all(
                [
                    Role(id_rol=1, nombre="administrador"),
                    Role(id_rol=2, nombre="estudiante"),
                    Role(id_rol=3, nombre="docente"),
                    Career(id_carrera=1, nombre="Sistemas", clave="ISC"),
                ]
            )
            await db.flush()
            users = [
                User(
                    id_rol=role_id,
                    nombre=name,
                    correo=email,
                    password_hash=password_hash,
                    debe_cambiar_contrasena=False,
                )
                for role_id, name, email in [
                    (1, "Administrador", "admin@example.com"),
                    (2, "Estudiante", "student@example.com"),
                    (3, "Docente", "teacher@example.com"),
                ]
            ]
            db.add_all(users)
            await db.flush()
            db.add_all(
                [
                    Student(id_usuario=users[1].id_usuario, id_carrera=1, matricula="20260001", semestre=1),
                    Teacher(id_usuario=users[2].id_usuario, numero_empleado="EMP001"),
                ]
            )
            await db.commit()
        yield factory
    finally:
        await engine.dispose()
        if owner is not None:
            async with owner.begin() as conn:
                await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            await owner.dispose()


@pytest_asyncio.fixture
async def client(database):
    async def override_db():
        async with database() as db:
            try:
                yield db
            except Exception:
                await db.rollback()
                raise

    app.dependency_overrides[get_db] = override_db
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
