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


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Requiere TEST_DATABASE_URL PostgreSQL aislado"
)
def test_postgres_migration_roundtrip_and_metadata():
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
            command.upgrade(config, "head")
            assert not compare_metadata(MigrationContext.configure(conn), Base.metadata)
            conn.commit()
            command.downgrade(config, "base")
            command.upgrade(config, "head")
            assert not compare_metadata(MigrationContext.configure(conn), Base.metadata)
            conn.commit()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
