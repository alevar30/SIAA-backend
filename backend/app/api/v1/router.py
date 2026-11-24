from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, academic, advising

# Router principal de la API
api_router = APIRouter(prefix="/api/v1")


@api_router.get("/ping")
async def ping() -> dict:
    """
    Endpoint de prueba. Sirve para confirmar que the router está montado
    y que la convención /api/v1/... funciona.
    """
    return {"message": "pong", "api_version": "v1"}


api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])

api_router.include_router(academic.admin_router, tags=["Catálogo administrativo"])
api_router.include_router(academic.public_router, tags=["Catálogo académico"])
api_router.include_router(academic.teacher_router, tags=["Docencia"])
api_router.include_router(advising.router)
