from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Tuple

from django.db import transaction

from core.models import Course, ClassSession


@dataclass(frozen=True)
class ImportRowError:
    line: int
    message: str


@dataclass(frozen=True)
class ImportResult:
    created: int
    updated: int
    skipped: int
    errors: List[ImportRowError]


def _parse_date(value: str) -> Optional[date]:
    v = (value or "").strip()
    if not v:
        return None

    # Preferido: YYYY-MM-DD
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Tolerância: DD/MM/YYYY
    try:
        return datetime.strptime(v, "%d/%m/%Y").date()
    except ValueError:
        return None


def _parse_int(value: str) -> Optional[int]:
    v = (value or "").strip()
    if not v:
        return None
    try:
        n = int(v)
        return n if n > 0 else None
    except ValueError:
        return None


def import_classes_from_csv(course: Course, uploaded_file) -> ImportResult:
    """
    CSV esperado (cabeçalho):
      date,title,class_number   (class_number opcional)

    Regras:
    - date e title obrigatórios
    - class_number opcional, mas recomendado
    - Identidade da aula:
        se class_number existe => (course, class_number)
        senão => (course, date, title)
    - Não mexe em watched/reviewed_* (importação não deve "marcar feito")
    """

    raw = uploaded_file.read()
    try:
        text = raw.decode("utf-8-sig")  # BOM-friendly
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    f = io.StringIO(text)
    reader = csv.DictReader(f)

    if not reader.fieldnames:
        return ImportResult(0, 0, 0, [ImportRowError(0, "CSV vazio ou sem cabeçalho.")])

    headers = {h.strip() for h in reader.fieldnames if h}
    if "date" not in headers or "title" not in headers:
        return ImportResult(
            0, 0, 0,
            [ImportRowError(0, "Cabeçalho inválido. Use: date,title,class_number (class_number opcional).")]
        )

    created = updated = skipped = 0
    errors: List[ImportRowError] = []
    rows: List[Tuple[int, date, str, Optional[int]]] = []

    for idx, row in enumerate(reader, start=2):  # linha 1 = cabeçalho
        d = _parse_date(row.get("date", ""))
        title = (row.get("title") or "").strip()
        class_number = _parse_int(row.get("class_number", ""))

        if not d:
            errors.append(ImportRowError(idx, f"Data inválida: '{row.get('date')}'. Use YYYY-MM-DD ou DD/MM/YYYY."))
            continue
        if not title:
            errors.append(ImportRowError(idx, "Título vazio."))
            continue

        rows.append((idx, d, title, class_number))

    if errors:
        return ImportResult(0, 0, 0, errors)

    with transaction.atomic():
        for idx, d, title, class_number in rows:
            if class_number is not None:
                # Identidade por número (melhor)
                obj, was_created = ClassSession.objects.get_or_create(
                    course=course,
                    class_number=class_number,
                    defaults={"date": d, "title": title},
                )

                if was_created:
                    created += 1
                else:
                    changed = False
                    if obj.date != d:
                        obj.date = d
                        changed = True
                    if obj.title != title:
                        obj.title = title
                        changed = True

                    if changed:
                        obj.save(update_fields=["date", "title"])
                        updated += 1
                    else:
                        skipped += 1
            else:
                # Fallback sem número: (course, date, title)
                obj, was_created = ClassSession.objects.get_or_create(
                    course=course,
                    date=d,
                    title=title,
                    defaults={"class_number": None},
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

    return ImportResult(created, updated, skipped, [])
