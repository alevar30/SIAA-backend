"""Servidor exclusivo para pruebas de navegador. Nunca conecta a la base real."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
import secrets

if os.getenv("SIAA_E2E") != "1":
    raise RuntimeError("Este servidor requiere SIAA_E2E=1 y solo debe usarse para pruebas locales")
os.environ.update(
    {
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_SERVER": "127.0.0.1",
        "POSTGRES_DB": "siaa_test",
        "SECRET_KEY": "e2e-only-91ccf1922361490bbaaf0ed24d24e9ba",
        "SQL_ECHO": "false",
    }
)
from sqlalchemy import BigInteger, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.main import app
from app.db.base import Base
from app.db.session import get_db, engine as production_engine
from app.models.user import Role, User
from app.models.profiles import Student, Teacher
from app.models.academic import Career
from app.core.security import get_password_hash


@compiles(BigInteger, "sqlite")
def sqlite_bigint(element, compiler, **kwargs):
    return "INTEGER"


@asynccontextmanager
async def lifespan(application):
    folder = Path(__file__).resolve().parents[1] / ".test-tmp"
    folder.mkdir(exist_ok=True)
    path = folder / ("browser_" + secrets.token_hex(8) + ".db")
    engine = create_async_engine("sqlite+aiosqlite:///" + path.as_posix())

    @event.listens_for(engine.sync_engine, "connect")
    def enable_fk(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override():
        async with factory() as db:
            try:
                yield db
            except Exception:
                await db.rollback()
                raise

    application.dependency_overrides[get_db] = override
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            db.add_all(
                [
                    Role(id_rol=1, nombre="administrador"),
                    Role(id_rol=2, nombre="estudiante"),
                    Role(id_rol=3, nombre="docente"),
                    Career(id_carrera=1, nombre="Ingeniería en Sistemas Computacionales", clave="ISC"),
                ]
            )
            await db.flush()
            hashed = get_password_hash("ClaveInicial123!")
            users = [
                User(
                    id_rol=role,
                    nombre=name,
                    correo=email,
                    password_hash=hashed,
                    debe_cambiar_contrasena=pending,
                )
                for role, name, email, pending in [
                    (1, "Administración SIAA", "admin@example.com", False),
                    (2, "Ana Estudiante", "student@example.com", False),
                    (3, "Juan Docente", "teacher@example.com", False),
                    (2, "Primer Acceso", "first@example.com", True),
                ]
            ]
            db.add_all(users)
            await db.flush()
            db.add_all(
                [
                    Student(id_usuario=users[1].id_usuario, id_carrera=1, matricula="20260001"),
                    Teacher(id_usuario=users[2].id_usuario, numero_empleado="EMP001"),
                    Student(id_usuario=users[3].id_usuario, id_carrera=1, matricula="20260002"),
                ]
            )
            await db.commit()
        yield
    finally:
        application.dependency_overrides.clear()
        await engine.dispose()
        await production_engine.dispose()
        path.unlink(missing_ok=True)


app.router.lifespan_context = lifespan
