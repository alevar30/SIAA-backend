from io import StringIO

from alembic import command
from alembic.config import Config


def test_migrations_generate_postgres_sql_without_database():
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE usuarios" in sql
    assert "ADD COLUMN token_version" in sql
    assert "CREATE UNIQUE INDEX uq_usuarios_correo_lower ON usuarios (lower(correo))" in sql
    assert "20261030_01" in sql
    assert "ADD COLUMN apellidos VARCHAR(150)" in sql
    assert "ALTER COLUMN correo DROP NOT NULL" in sql
    assert "ALTER COLUMN id_carrera DROP NOT NULL" in sql
