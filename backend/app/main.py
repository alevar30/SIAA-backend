from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.v1.router import api_router

app = FastAPI(title="SIAA API")

# Monta toda la API bajo el prefijo /api/v1
app.include_router(api_router)

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