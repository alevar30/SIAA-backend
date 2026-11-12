import pytest
from sqlalchemy import delete, select

import app.manage as management
from app.models.user import Role, User
from app.models.profiles import Student, Teacher


async def test_bootstrap_cannot_create_second_admin(database, monkeypatch):
    monkeypatch.setattr(management, "AsyncSessionLocal", database)
    with pytest.raises(ValueError, match="Ya existe"):
        await management.manage("bootstrap-admin", "other@example.com", "Otro Administrador")


async def test_bootstrap_admin_empty_database(database, monkeypatch):
    monkeypatch.setattr(management, "AsyncSessionLocal", database)
    async with database() as db:
        for model in (Student, Teacher, User, Role):
            await db.execute(delete(model))
        await db.commit()
    password = await management.manage("bootstrap-admin", "fresh@example.com", "Nuevo Administrador")
    assert len(password) == 24
    async with database() as db:
        user = await db.scalar(select(User).where(User.correo == "fresh@example.com"))
        assert user.debe_cambiar_contrasena


async def test_reset_revokes_sessions_and_forces_change(database, monkeypatch):
    monkeypatch.setattr(management, "AsyncSessionLocal", database)
    async with database() as db:
        user = await db.scalar(select(User).where(User.correo == "admin@example.com"))
        version = user.token_version
    await management.manage("reset-password", "ADMIN@example.com")
    async with database() as db:
        user = await db.scalar(select(User).where(User.correo == "admin@example.com"))
        assert user.token_version == version + 1
        assert user.debe_cambiar_contrasena


async def test_reset_unknown_account(database, monkeypatch):
    monkeypatch.setattr(management, "AsyncSessionLocal", database)
    with pytest.raises(ValueError, match="no encontrado"):
        await management.manage("reset-password", "missing@example.com")
