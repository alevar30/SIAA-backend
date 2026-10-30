from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Cargar todos los modelos para que los mappers de SQLAlchemy se registren
import app.models.user  # noqa
import app.models.academic  # noqa
import app.models.profiles  # noqa

from app.db.session import get_db
from app.api.v1.router import api_router
from app.api.v1.endpoints import auth

app = FastAPI(title="SIAA API")

# Configuración CORS para desarrollo
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta toda la API bajo el prefijo /api/v1
app.include_router(api_router)
# Montaje directo por seguridad
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])



@app.get("/health-db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """
    Ruta de prueba para verificar la conexión asíncrona a PostgreSQL.
    """
    try:
        # Ejecutamos una consulta simple de prueba
        result = await db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "db_connection": "Exitosa",
            "result": result.scalar()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al conectar con la Base de Datos: {str(e)}"
        }