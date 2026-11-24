from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Annotated

AcademicId = Annotated[int, Field(strict=True, gt=0, le=2147483647)]


class CareerWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    nombre: str = Field(min_length=3, max_length=150)
    clave: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")
    activo: bool = True

    @field_validator("clave")
    @classmethod
    def normalize_key(cls, value):
        return value.upper()


class CareerEdit(CareerWrite):
    version: int = Field(ge=1, le=2147483647, strict=True)


class CareerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nombre: str
    clave: str
    activo: bool
    id_carrera: int
    version: int


class SubjectWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    nombre: str = Field(min_length=3, max_length=150)
    clave: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    activo: bool = True
    carrera_ids: list[AcademicId] = Field(min_length=1, max_length=200)

    @field_validator("clave")
    @classmethod
    def normalize_key(cls, value):
        return value.upper()

    @field_validator("carrera_ids")
    @classmethod
    def unique_ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("No se permiten carreras duplicadas")
        return value


class SubjectEdit(SubjectWrite):
    version: int = Field(ge=1, le=2147483647, strict=True)


class SubjectRead(BaseModel):
    id_materia: int
    nombre: str
    clave: str
    activo: bool
    version: int
    carreras: list[CareerRead]


class TopicWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: str | None = Field(default=None, max_length=2000)
    activo: bool = True


class TopicCreate(TopicWrite):
    id_materia: AcademicId


class TopicEdit(TopicWrite):
    version: int = Field(ge=1, le=2147483647, strict=True)


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nombre: str
    descripcion: str | None
    activo: bool
    id_tema: int
    id_materia: int
    version: int
    id_creador: int | None = None
    creador_nombre: str | None = None
    tiene_asesorias: bool = False


class AssignmentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    materia_ids: list[AcademicId] = Field(max_length=500)
    version: int = Field(ge=1, le=2147483647, strict=True)

    @field_validator("materia_ids")
    @classmethod
    def unique_ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("No se permiten materias duplicadas")
        return value


class TopicSelectionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tema_ids: list[AcademicId] = Field(max_length=1000)
    version: int = Field(ge=1, le=2147483647, strict=True)

    @field_validator("tema_ids")
    @classmethod
    def unique_ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("No se permiten temas duplicados")
        return value


class TeachingSubject(SubjectRead):
    temas: list[TopicRead]
    tema_ids: list[int]


class TeacherRead(BaseModel):
    id_docente: int
    id_usuario: int
    nombre: str
    numero_empleado: str
    departamento: str | None
    activo: bool
    version: int
    materias: list[TeachingSubject]


class TeacherList(BaseModel):
    items: list[TeacherRead]
    total: int
    page: int
    page_size: int
