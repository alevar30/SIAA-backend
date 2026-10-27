from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Crea el motor de base de datos asíncrono
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=True,  # Muestra en consola las consultas SQL generadas (útil para aprender)
    future=True,
)

# Fábrica para generar sesiones de BD en cada petición HTTP
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Inyección de Dependencia de FastAPI:
    Abre una sesión de BD para la petición y la cierra automáticamente al terminar.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
