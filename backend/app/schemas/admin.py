from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreateBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nombre: str = Field(min_length=3, max_length=150)
    correo: EmailStr = Field(max_length=150)

    @field_validator("correo")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class AltaEstudianteRequest(UserCreateBase):
    matricula: str = Field(min_length=4, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    id_carrera: int = Field(gt=0, le=2147483647)
    semestre: int | None = Field(default=None, ge=1, le=12)


class AltaDocenteRequest(UserCreateBase):
    numero_empleado: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    departamento: str | None = Field(default=None, max_length=100)


class UsuarioCreadoResponse(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    rol: str
    password_temporal: str
    debe_cambiar_contrasena: bool
    mensaje: str


class CareerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_carrera: int
    nombre: str
    clave: str
    activo: bool


class CareerCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nombre: str = Field(min_length=3, max_length=150)
    clave: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("clave")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return value.upper()


class UserSummaryResponse(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
    rol: str
    activo: bool
    debe_cambiar_contrasena: bool
    matricula: str | None = None
    carrera: str | None = None
    semestre: int | None = None
    numero_empleado: str | None = None
    departamento: str | None = None


class UserListResponse(BaseModel):
    items: list[UserSummaryResponse]
    total: int
    page: int
    page_size: int


class AdminSummaryResponse(BaseModel):
    estudiantes: int
    docentes: int
    administradores: int
    carreras_activas: int
