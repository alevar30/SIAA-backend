from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest

repo = AuthRepository()


class AuthService:
    @staticmethod
    async def login(db: AsyncSession, datos: LoginRequest):
        usuario = None
        # 1) Intentar por correo
        usuario = await repo.get_by_correo(db, datos.identificador)
        # 2) Intentar por matrícula (estudiante)
        if not usuario:
            usuario = await repo.get_by_matricula(db, datos.identificador)
        # 3) Intentar por número de empleado (docente)
        if not usuario:
            usuario = await repo.get_by_numero_empleado(db, datos.identificador)

        if not usuario:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

        if not usuario.activo:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario desactivado")

        if not verify_password(datos.password, usuario.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

        token_data = {
            "sub": str(usuario.id_usuario),
            "id_usuario": usuario.id_usuario,
            "rol": usuario.rol.nombre if usuario.rol else None,
            "debe_cambiar_contrasena": usuario.debe_cambiar_contrasena,
        }
        access_token = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "debe_cambiar_contrasena": usuario.debe_cambiar_contrasena,
            "requiere_cambio_contrasena": usuario.debe_cambiar_contrasena,
            "id_usuario": usuario.id_usuario,
            "nombre": usuario.nombre,
            "rol": usuario.rol.nombre if usuario.rol else None,
        }

    @staticmethod
    async def cambiar_contrasena(db: AsyncSession, id_usuario: int, datos: ChangePasswordRequest):
        if datos.password_nueva != datos.password_nueva_confirm:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Las contraseñas nuevas no coinciden")

        usuario = await repo.get_by_id(db, id_usuario)
        if not usuario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        if not verify_password(datos.password_actual, usuario.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual inválida")

        new_hash = get_password_hash(datos.password_nueva)
        usuario = await repo.update_password(db, usuario, new_hash)
        return {"message": "Contraseña actualizada correctamente", "debe_cambiar_contrasena": usuario.debe_cambiar_contrasena}
