import csv
from dataclasses import dataclass
from io import StringIO, TextIOWrapper

from study.models import StudyPlan, StudyQuestion, StudySource, StudyTag


@dataclass
class ImportError:
    line: int
    message: str


@dataclass
class ImportResult:
    created: int
    errors: list[ImportError]


REQUIRED_FIELDS = {
    "area",
    "tema",
    "subtema",
    "enunciado",
    "choice_a",
    "choice_b",
    "choice_c",
    "choice_d",
    "choice_e",
    "correct_choice",
}


def _clean(value):
    return (value or "").strip()


def _import_questions_from_reader(reader, *, user) -> ImportResult:
    errors: list[ImportError] = []
    created = 0

    if not reader.fieldnames:
        return ImportResult(created=0, errors=[ImportError(line=1, message="CSV sem cabeçalho.")])

    header = {h.strip() for h in reader.fieldnames if h}
    missing = [field for field in sorted(REQUIRED_FIELDS) if field not in header]
    if missing:
        return ImportResult(created=0, errors=[ImportError(line=1, message=f"Colunas obrigatórias ausentes: {', '.join(missing)}")])

    for idx, row in enumerate(reader, start=2):
        area = _clean(row.get("area"))
        tema = _clean(row.get("tema"))
        subtema = _clean(row.get("subtema"))
        enunciado = _clean(row.get("enunciado"))
        choice_a = _clean(row.get("choice_a"))
        choice_b = _clean(row.get("choice_b"))
        choice_c = _clean(row.get("choice_c"))
        choice_d = _clean(row.get("choice_d"))
        choice_e = _clean(row.get("choice_e"))
        correct_choice = _clean(row.get("correct_choice")).upper()

        if not all([area, tema, subtema, enunciado, choice_a, choice_b, choice_c, choice_d, choice_e, correct_choice]):
            errors.append(ImportError(line=idx, message="Campos obrigatórios vazios."))
            continue
        if correct_choice not in {"A", "B", "C", "D", "E"}:
            errors.append(ImportError(line=idx, message="correct_choice deve ser A, B, C, D ou E."))
            continue

        difficulty = _clean(row.get("difficulty")).upper() or "MEDIUM"
        if difficulty not in {"EASY", "MEDIUM", "HARD"}:
            errors.append(ImportError(line=idx, message="difficulty inválido (EASY, MEDIUM, HARD)."))
            continue

        tag, _ = StudyTag.objects.get_or_create(area=area, tema=tema, subtema=subtema)

        source = None
        source_instituicao = _clean(row.get("source_instituicao"))
        source_prova = _clean(row.get("source_prova"))
        source_ano = _clean(row.get("source_ano"))
        if source_instituicao and source_prova:
            ano_int = None
            if source_ano:
                try:
                    ano_int = int(source_ano)
                except ValueError:
                    errors.append(ImportError(line=idx, message="source_ano deve ser número."))
                    continue
            source, _ = StudySource.objects.get_or_create(
                instituicao=source_instituicao,
                prova_nome=source_prova,
                ano=ano_int,
            )

        plan = None
        plan_name = _clean(row.get("plan_name"))
        if plan_name:
            plan, _ = StudyPlan.objects.get_or_create(user=user, name=plan_name)

        source_page = None
        source_page_raw = _clean(row.get("source_page"))
        if source_page_raw:
            try:
                source_page = int(source_page_raw)
            except ValueError:
                errors.append(ImportError(line=idx, message="source_page deve ser número."))
                continue

        source_snippet = _clean(row.get("source_snippet"))
        explanation = _clean(row.get("explanation"))

        StudyQuestion.objects.create(
            tag=tag,
            source=source,
            plan=plan,
            enunciado=enunciado,
            choice_a=choice_a,
            choice_b=choice_b,
            choice_c=choice_c,
            choice_d=choice_d,
            choice_e=choice_e,
            correct_choice=correct_choice,
            explanation=explanation,
            difficulty=difficulty,
            source_page=source_page,
            source_snippet=source_snippet,
        )
        created += 1

    return ImportResult(created=created, errors=errors)


def import_questions_from_csv(file_obj, *, user) -> ImportResult:
    errors: list[ImportError] = []
    created = 0

    reader = csv.DictReader(TextIOWrapper(file_obj, encoding="utf-8-sig"))
    return _import_questions_from_reader(reader, user=user)


def import_questions_from_csv_text(text: str, *, user) -> ImportResult:
    reader = csv.DictReader(StringIO(text))
    return _import_questions_from_reader(reader, user=user)
