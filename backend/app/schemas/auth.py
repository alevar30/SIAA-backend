from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Solo número de control (matrícula)."""
    identificador: str = Field(min_length=3, description="Número de control")
    password: str = Field(min_length=4)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    debe_cambiar_contrasena: bool
    requiere_cambio_contrasena: bool
    id_usuario: int
    nombre: str
    rol: str


class ChangePasswordRequest(BaseModel):
    password_actual: str = Field(min_length=4)
    password_nueva: str = Field(min_length=6)
    password_nueva_confirm: str = Field(min_length=6)
