"""Pruebas exclusivas de PostgreSQL; cada ejecución usa un esquema desechable."""

import os
import secrets

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from app.db.base import Base


@pytest.fixture
def migration_database():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("Requiere TEST_DATABASE_URL PostgreSQL aislado")
    url = os.environ["TEST_DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    schema = "siaa_migration_" + secrets.token_hex(8)
    engine = create_engine(url)
    config = Config("alembic.ini")
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as conn:
            conn.execute(text(f'SET search_path TO "{schema}"'))
            conn.commit()
            config.attributes["connection"] = conn
            yield conn, config
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_postgres_migration_roundtrip_and_metadata(migration_database):
    conn, config = migration_database
    command.upgrade(config, "head")
    assert not compare_metadata(MigrationContext.configure(conn), Base.metadata)
    conn.commit()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert not compare_metadata(MigrationContext.configure(conn), Base.metadata)
    conn.commit()


def test_catalog_migration_preserves_existing_records(migration_database):
    conn, config = migration_database
    command.upgrade(config, "20261111_01")
    conn.execute(text("INSERT INTO carreras(id_carrera,nombre,clave,activo) VALUES(1,'Sistemas','ISC',true)"))
    conn.execute(
        text("INSERT INTO materias(id_materia,nombre,clave,activo) VALUES(1,'Materia anterior','OLD',true)")
    )
    conn.execute(text("INSERT INTO temas(id_tema,id_materia,nombre,activo) VALUES(1,1,'Tema anterior',true)"))
    conn.execute(text("INSERT INTO roles(id_rol,nombre,activo) VALUES(1,'docente',true)"))
    conn.execute(
        text(
            "INSERT INTO usuarios(id_usuario,id_rol,nombre,password_hash,activo,debe_cambiar_contrasena,fecha_creacion) VALUES(1,1,'Docente anterior','hash-test',true,false,now())"
        )
    )
    conn.execute(text("INSERT INTO docentes(id_docente,id_usuario,numero_empleado) VALUES(1,1,'OLD001')"))
    conn.commit()
    command.upgrade(config, "head")
    assert conn.execute(text("SELECT nombre,version FROM materias WHERE id_materia=1")).one() == (
        "Materia anterior",
        1,
    )
    assert conn.execute(text("SELECT nombre,version FROM temas WHERE id_tema=1")).one() == (
        "Tema anterior",
        1,
    )
    assert conn.execute(text("SELECT academic_version FROM docentes WHERE id_docente=1")).scalar_one() == 1
    assert conn.execute(text("SELECT id_creador FROM temas WHERE id_tema=1")).scalar_one() is None
    conn.execute(text("INSERT INTO carrera_materia(id_carrera,id_materia) VALUES(1,1)"))
    conn.execute(text("INSERT INTO docente_materia(id_docente,id_materia) VALUES(1,1)"))
    conn.execute(text("INSERT INTO docente_tema(id_docente,id_tema,id_materia) VALUES(1,1,1)"))
    conn.commit()
    command.downgrade(config, "20261111_01")
    assert (
        conn.execute(text("SELECT nombre FROM materias WHERE id_materia=1")).scalar_one()
        == "Materia anterior"
    )
    assert (
        conn.execute(text("SELECT nombre FROM usuarios WHERE id_usuario=1")).scalar_one()
        == "Docente anterior"
    )
    conn.commit()
