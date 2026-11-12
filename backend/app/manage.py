"""Herramientas locales de administración; no se exponen por HTTP."""

import argparse
import asyncio
from datetime import datetime, timezone

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

import app.models.academic  # noqa: F401
import app.models.profiles  # noqa: F401
from app.core.security import generate_temporary_password, get_password_hash
from app.db.session import AsyncSessionLocal, engine
from app.models.user import Role, User


async def manage(command: str, correo: str, nombre: str | None = None) -> str:
    if command not in {"bootstrap-admin", "reset-password"}:
        raise ValueError("Operación desconocida")
    correo = str(TypeAdapter(EmailStr).validate_python(correo)).lower()
    if len(correo) > 150:
        raise ValueError("El correo no puede superar 150 caracteres")
    password = generate_temporary_password()
    async with AsyncSessionLocal() as db:
        try:
            if command == "bootstrap-admin":
                if not nombre or not 3 <= len(nombre.strip()) <= 150:
                    raise ValueError("El nombre debe tener entre 3 y 150 caracteres")
                for role_name in ("administrador", "estudiante", "docente"):
                    if not await db.scalar(select(Role).where(Role.nombre == role_name)):
                        db.add(Role(nombre=role_name))
                await db.flush()
                role = await db.scalar(select(Role).where(Role.nombre == "administrador"))
                if not role.activo:
                    raise ValueError("El rol administrador está desactivado")
                existing = await db.scalar(select(User.id_usuario).where(User.id_rol == role.id_rol).limit(1))
                if existing:
                    raise ValueError(
                        "Ya existe un administrador; utiliza reset-password si perdiste su contraseña"
                    )
                db.add(
                    User(
                        id_rol=role.id_rol,
                        nombre=nombre.strip(),
                        correo=correo,
                        password_hash=get_password_hash(password),
                        debe_cambiar_contrasena=True,
                    )
                )
            else:
                usuario = await db.scalar(select(User).where(func.lower(User.correo) == correo))
                if not usuario:
                    raise ValueError("Usuario no encontrado")
                await db.execute(
                    update(User)
                    .where(User.id_usuario == usuario.id_usuario)
                    .values(
                        password_hash=get_password_hash(password),
                        debe_cambiar_contrasena=True,
                        token_version=User.token_version + 1,
                        fecha_ultimo_cambio=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                )
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return password


def main():
    parser = argparse.ArgumentParser(description="Administración local de cuentas SIAA")
    parser.add_argument("command", choices=["bootstrap-admin", "reset-password"])
    parser.add_argument("--correo", required=True)
    parser.add_argument("--nombre")
    args = parser.parse_args()

    async def run():
        try:
            password = await manage(args.command, args.correo, args.nombre)
            print("Operación completada. Contraseña temporal (entregar por un canal privado):")
            print(password)
        finally:
            await engine.dispose()

    try:
        asyncio.run(run())
    except (ValueError, IntegrityError) as exc:
        parser.exit(
            1,
            "No se completó la operación: "
            + (str(exc) if isinstance(exc, ValueError) else "datos duplicados")
            + "\n",
        )


if __name__ == "__main__":
    main()
