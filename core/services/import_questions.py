import csv
import io
from dataclasses import dataclass

from core.models import Question, QuestionOption


@dataclass
class ImportErrorItem:
    line: int
    message: str


@dataclass
class ImportResult:
    created: int
    errors: list


def _get_value(row, keys):
    for key in keys:
        if key in row:
            return (row.get(key) or "").strip()
    return ""


def import_questions_from_csv_text(course, text, classes=None):
    reader = csv.DictReader(io.StringIO(text))
    required = ["enunciado", "alternativa_a", "alternativa_b", "alternativa_c", "alternativa_d", "correta"]
    if not reader.fieldnames:
        return ImportResult(created=0, errors=[ImportErrorItem(1, "CSV sem cabeçalho.")])

    missing = [c for c in required if c not in reader.fieldnames]
    if missing:
        msg = "Cabeçalhos ausentes: " + ", ".join(missing)
        return ImportResult(created=0, errors=[ImportErrorItem(1, msg)])

    created = 0
    errors = []

    for idx, row in enumerate(reader, start=2):
        enunciado = _get_value(row, ["enunciado"])
        alt_a = _get_value(row, ["alternativa_a"])
        alt_b = _get_value(row, ["alternativa_b"])
        alt_c = _get_value(row, ["alternativa_c"])
        alt_d = _get_value(row, ["alternativa_d"])
        correta = _get_value(row, ["correta"]).upper()
        tema = _get_value(row, ["tema", "topic"])
        resolucao = _get_value(row, ["resolucao", "resolução", "resolution"])

        if not enunciado:
            errors.append(ImportErrorItem(idx, "Enunciado vazio."))
            continue
        if not (alt_a and alt_b):
            errors.append(ImportErrorItem(idx, "É preciso pelo menos A e B."))
            continue
        if correta not in {"A", "B", "C", "D"}:
            errors.append(ImportErrorItem(idx, "Campo 'correta' deve ser A, B, C ou D."))
            continue

        options = {"A": alt_a, "B": alt_b, "C": alt_c, "D": alt_d}
        if not options.get(correta):
            errors.append(ImportErrorItem(idx, "Alternativa correta sem texto."))
            continue

        if tema:
            tema = " ".join(tema.split())
        question = Question.objects.create(course=course, title=enunciado, topic=tema, resolution=resolucao)
        if classes is not None:
            question.classes.add(*classes)
        for letter, text_opt in options.items():
            if not text_opt:
                continue
            QuestionOption.objects.create(
                question=question,
                text=text_opt,
                is_correct=(letter == correta),
            )
        created += 1

    return ImportResult(created=created, errors=errors)


def import_questions_from_csv(course, uploaded_file, classes=None):
    raw = uploaded_file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return import_questions_from_csv_text(course, text, classes=classes)
