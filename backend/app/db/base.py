from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Clase base de la que heredan TODOS los modelos SQLAlchemy.

    ¿Por qué existe?
    - SQLAlchemy necesita un punto común donde registrar cada tabla.
    - Al heredar de `DeclarativeBase`, cada modelo que se declara se guarda
      automáticamente en `Base.metadata`.
    - Alembic lee `Base.metadata` para saber qué tablas debe crear/actualizar.

    ¿Por qué `DeclarativeBase` y no `declarative_base()`?
    - `declarative_base()` es el estilo antiguo (SQLAlchemy 1.x).
    - El estilo moderno 2.0 (el que usan nuestros modelos con `Mapped[...]`)
      es heredar de `DeclarativeBase`. Mantener un solo estilo evita errores.
    """
    pass
