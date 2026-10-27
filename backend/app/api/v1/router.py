from fastapi import APIRouter

# Router principal de la API. Aquí se agregarán (en pasos futuros) los routers
# de cada módulo: usuarios, estudiantes, docentes, carreras, materias, etc.
api_router = APIRouter(prefix="/api/v1")


@api_router.get("/ping")
async def ping() -> dict:
    """
    Endpoint de prueba. Sirve para confirmar que el router está montado
    y que la convención /api/v1/... funciona.
    """
    return {"message": "pong", "api_version": "v1"}