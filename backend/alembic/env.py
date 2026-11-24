from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Configuración y modelos del proyecto
from app.core.config import settings
from app.db.base import Base

# Importa TODOS los modelos para que Alembic detecte las tablas
import app.models.user  # noqa: F401
import app.models.academic  # noqa: F401
import app.models.profiles  # noqa: F401
import app.models.advising  # noqa: F401

config = context.config

# Configura el logging según la sección [loggers] de alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """
    URL para las MIGRACIONES.

    La app usa asyncpg (asíncrono), pero Alembic ejecuta las migraciones
    en modo SÍNCRONO, así que se cambia el driver a psycopg.
    """
    return settings.ASYNC_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def run_migrations_offline() -> None:
    """Migraciones 'offline': genera SQL sin conectarse a la BD."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Migraciones 'online': se conecta a la BD y ejecuta las sentencias."""
    # Permite migraciones verificadas dentro de un esquema de prueba aislado.
    provided_connection = config.attributes.get("connection")
    if provided_connection is not None:
        context.configure(connection=provided_connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

    # Se parte de la configuración de alembic.ini y se inyecta la URL real
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
