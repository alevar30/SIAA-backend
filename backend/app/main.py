import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Registrar los modelos antes de configurar sus relaciones.
import app.models.user  # noqa: F401
import app.models.academic  # noqa: F401
import app.models.profiles  # noqa: F401
from app.core.config import settings
from app.db.session import engine, get_db
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health-db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        logger.warning("La comprobación de disponibilidad de la base de datos falló")
        raise HTTPException(status_code=503, detail="Base de datos no disponible") from None
    return {"status": "ok", "db_connection": "Exitosa", "result": 1}
