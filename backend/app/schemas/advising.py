from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.schemas.academic import AcademicId


class IntervalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    inicio: AwareDatetime
    fin: AwareDatetime

    @model_validator(mode="after")
    def validate_interval(self):
        self.inicio = self.inicio.astimezone(timezone.utc)
        self.fin = self.fin.astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        if self.inicio <= now or self.inicio > now + timedelta(days=180):
            raise ValueError("El inicio debe ser futuro y estar dentro de los próximos 180 días")
        if not timedelta(minutes=15) <= self.fin - self.inicio <= timedelta(hours=8):
            raise ValueError("El intervalo debe durar entre 15 minutos y 8 horas")
        return self


class AvailabilityCreate(IntervalInput):
    modalidad: Literal["presencial", "virtual"]
    ubicacion: str = Field(min_length=3, max_length=300)

    @model_validator(mode="after")
    def validate_location(self):
        if self.modalidad == "virtual":
            from urllib.parse import urlsplit

            url = urlsplit(self.ubicacion)
            if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password:
                raise ValueError("Indica un enlace HTTP(S) de reunión válido y sin credenciales")
        return self


class VersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: int = Field(strict=True, ge=1, le=2147483647)


class SessionCreate(IntervalInput):
    id_disponibilidad: AcademicId
    id_tema: AcademicId
    tipo: Literal["individual", "grupal"]
    cupo_maximo: int = Field(strict=True, ge=1, le=50)

    @model_validator(mode="after")
    def validate_capacity(self):
        if (self.tipo == "individual" and self.cupo_maximo != 1) or (
            self.tipo == "grupal" and self.cupo_maximo < 2
        ):
            raise ValueError("Individual requiere un lugar; grupal, entre 2 y 50")
        if self.fin - self.inicio > timedelta(hours=4):
            raise ValueError("La asesoría no puede durar más de cuatro horas")
        return self


class CancelInput(VersionInput):
    motivo: str = Field(min_length=5, max_length=500)


class AttendanceInput(VersionInput):
    asistieron: list[AcademicId] = Field(max_length=50)

    @model_validator(mode="after")
    def unique_students(self):
        if len(self.asistieron) != len(set(self.asistieron)):
            raise ValueError("No se permiten estudiantes duplicados")
        return self


class AvailabilityRead(BaseModel):
    id_disponibilidad: int
    inicio: datetime
    fin: datetime
    modalidad: str
    ubicacion: str
    estado: str
    version: int


class ReservationRead(BaseModel):
    estado: str
    version: int


class SessionRead(BaseModel):
    id_asesoria: int
    id_docente: int
    docente: str
    materia: str
    id_materia: int
    tema: str
    id_tema: int
    inicio: datetime
    fin: datetime
    modalidad: str
    ubicacion: str
    tipo: str
    cupo_maximo: int
    ocupados: int
    disponibles: int
    estado: str
    motivo_cancelacion: str | None
    version: int
    mi_reserva: ReservationRead | None


class SessionList(BaseModel):
    items: list[SessionRead]
    total: int
    page: int
    page_size: int


class ParticipantRead(BaseModel):
    id_estudiante: int
    nombre: str
    matricula: str
    estado: str


class SessionDetail(SessionRead):
    participantes: list[ParticipantRead]
