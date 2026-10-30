from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class AltaEstudianteRequest(BaseModel):
    nombre: str = Field(min_length=3, max_length=150)
    correo: EmailStr
    matricula: str = Field(min_length=4, max_length=30)
    id_carrera: int
    semestre: Optional[int] = Field(default=None, ge=1, le=12)


class AltaDocenteRequest(BaseModel):
    nombre: str = Field(min_length=3, max_length=150)
    correo: EmailStr
    numero_empleado: str = Field(min_length=3, max_length=30)
    departamento: Optional[str] = Field(default=None, max_length=100)


class UsuarioCreadoResponse(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    rol: str
    password_generica: str
    debe_cambiar_contrasena: bool
    mensaje: str
