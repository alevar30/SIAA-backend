from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.models.profiles import Student, Teacher
from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import AltaDocenteRequest, AltaEstudianteRequest

repo = AdminRepository()


class AdminService:
    @staticmethod
    async def alta_estudiante(db: AsyncSession, datos: AltaEstudianteRequest):
        # Validaciones
        if await repo.get_user_by_correo(db, datos.correo):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un usuario con ese correo")

        if await repo.get_student_by_matricula(db, datos.matricula):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un estudiante con esa matrícula")

        rol = await repo.get_role_by_name(db, "estudiante")
        if not rol:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Rol 'estudiante' no encontrado")

        password_generica = f"SIAA-{datos.matricula}"
        password_hash = get_password_hash(password_generica)

        usuario = User(
            id_rol=rol.id_rol,
            nombre=datos.nombre,
            correo=datos.correo,
            password_hash=password_hash,
            activo=True,
            debe_cambiar_contrasena=True,
        )
        db.add(usuario)
        await db.flush()

        estudiante = Student(
            id_usuario=usuario.id_usuario,
            id_carrera=datos.id_carrera,
            matricula=datos.matricula,
            semestre=datos.semestre,
        )
        db.add(estudiante)
        await db.commit()
        await db.refresh(usuario)

        return {
            "id_usuario": usuario.id_usuario,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "rol": rol.nombre,
            "password_generica": password_generica,
            "debe_cambiar_contrasena": True,
            "mensaje": "Estudiante dado de alta correctamente. Debe cambiar su contraseña al primer inicio.",
        }

    @staticmethod
    async def alta_docente(db: AsyncSession, datos: AltaDocenteRequest):
        if await repo.get_user_by_correo(db, datos.correo):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un usuario con ese correo")

        if await repo.get_teacher_by_numero_empleado(db, datos.numero_empleado):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un docente con ese número de empleado")

        rol = await repo.get_role_by_name(db, "docente")
        if not rol:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Rol 'docente' no encontrado")

        password_generica = f"SIAA-{datos.numero_empleado}"
        password_hash = get_password_hash(password_generica)

        usuario = User(
            id_rol=rol.id_rol,
            nombre=datos.nombre,
            correo=datos.correo,
            password_hash=password_hash,
            activo=True,
            debe_cambiar_contrasena=True,
        )
        db.add(usuario)
        await db.flush()

        docente = Teacher(
            id_usuario=usuario.id_usuario,
            numero_empleado=datos.numero_empleado,
            departamento=datos.departamento,
        )
        db.add(docente)
        await db.commit()
        await db.refresh(usuario)

        return {
            "id_usuario": usuario.id_usuario,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
            "rol": rol.nombre,
            "password_generica": password_generica,
            "debe_cambiar_contrasena": True,
            "mensaje": "Docente dado de alta correctamente. Debe cambiar su contraseña al primer inicio.",
        }
