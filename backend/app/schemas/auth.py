from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    identificador: str = Field(
        min_length=3, max_length=150, description="Correo, matrícula o número de empleado"
    )
    password: str = Field(min_length=4, max_length=72)

    @field_validator("identificador", mode="before")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes UTF-8")
        return value


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    debe_cambiar_contrasena: bool
    requiere_cambio_contrasena: bool
    id_usuario: int
    nombre: str
    rol: str


class ChangePasswordRequest(BaseModel):
    password_actual: str = Field(min_length=4, max_length=72)
    password_nueva: str = Field(min_length=12, max_length=72)
    password_nueva_confirm: str = Field(min_length=12, max_length=72)

    @field_validator("password_actual", "password_nueva", "password_nueva_confirm")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes UTF-8")
        return value


class ChangePasswordResponse(BaseModel):
    message: str
    debe_cambiar_contrasena: bool
    requiere_nuevo_login: bool


class CompleteStudentProfileRequest(ChangePasswordRequest):
    nombre: str = Field(min_length=1, max_length=150)
    apellidos: str = Field(min_length=1, max_length=150)
    id_carrera: int = Field(gt=0, le=2147483647)

    @field_validator("nombre", "apellidos", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class CurrentUserResponse(BaseModel):
    id_usuario: int
    nombre: str
    correo: str | None
    rol: str
    debe_cambiar_contrasena: bool
    requiere_completar_perfil: bool
    matricula: str | None = None
    carrera: str | None = None
    id_estudiante: int | None = None
    id_docente: int | None = None
