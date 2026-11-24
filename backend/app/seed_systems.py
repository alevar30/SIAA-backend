"""Registro reproducible de materias de la retícula de Sistemas proporcionada."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.models.profiles  # noqa: F401
import app.models.user  # noqa: F401
from app.models.academic import Career, CareerSubject, Subject
from app.schemas.academic import SubjectWrite


def load_subjects(career_id: int) -> list[SubjectWrite]:
    source = json.loads((Path(__file__).parent / "data/reticula_sistemas.json").read_text(encoding="utf-8"))
    subjects = [
        SubjectWrite(nombre=row["nombre"], clave=row["clave"], carrera_ids=[career_id])
        for row in source["materias"]
    ]
    if len({row.clave for row in subjects}) != len(subjects):
        raise ValueError("La retícula contiene claves duplicadas")
    return subjects


async def import_subjects(db: AsyncSession, career_key: str = "ISC", *, apply: bool = False) -> dict:
    """Prevalida todo el lote y confirma una sola transacción; repetir no duplica."""
    async with db.begin():
        career = await db.scalar(
            select(Career).where(func.upper(Career.clave) == career_key.upper()).with_for_update()
        )
        if career is None or not career.activo:
            raise ValueError("La carrera indicada debe existir y estar activa")
        rows = load_subjects(career.id_carrera)
        existing = (
            await db.scalars(
                select(Subject)
                .where(func.upper(Subject.clave).in_([row.clave for row in rows]))
                .order_by(Subject.id_materia)
                .with_for_update()
            )
        ).all()
        by_key = {row.clave.upper(): row for row in existing}
        if len(by_key) != len(existing):
            raise ValueError("Hay claves duplicadas en la base de datos")
        links = set(
            (
                await db.scalars(
                    select(CareerSubject.id_materia).where(CareerSubject.id_carrera == career.id_carrera)
                )
            ).all()
        )
        for row in rows:
            subject = by_key.get(row.clave)
            if subject and (subject.nombre != row.nombre or not subject.activo):
                raise ValueError(
                    f"Revisar conflicto de nombre o estado en {row.clave}; no se importó el lote"
                )
        new_count = sum(row.clave not in by_key for row in rows)
        linked_count = sum(row.id_materia not in links for row in existing)
        result = {
            "carrera": career.clave,
            "total_reticula": len(rows),
            "materias_nuevas": new_count,
            "asociaciones_nuevas": new_count + linked_count,
            "ya_registradas": len(existing),
            "aplicado": apply,
        }
        if apply:
            for row in rows:
                subject = by_key.get(row.clave)
                if subject is None:
                    subject = Subject(nombre=row.nombre, clave=row.clave, activo=True)
                    db.add(subject)
                    await db.flush()
                elif subject.id_materia not in links:
                    subject.version += 1
                if subject.id_materia not in links:
                    db.add(CareerSubject(id_carrera=career.id_carrera, id_materia=subject.id_materia))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrera", default="ISC", help="Clave de una carrera existente y activa")
    parser.add_argument(
        "--apply", action="store_true", help="Guardar; sin esta opción solo muestra la previsión"
    )
    args = parser.parse_args()

    async def run():
        from app.db.session import AsyncSessionLocal, engine

        try:
            async with AsyncSessionLocal() as db:
                print(
                    json.dumps(await import_subjects(db, args.carrera, apply=args.apply), ensure_ascii=False)
                )
        finally:
            await engine.dispose()

    try:
        asyncio.run(run())
    except ValueError as exc:
        parser.exit(1, f"No se completó el registro: {exc}\n")


if __name__ == "__main__":
    main()
