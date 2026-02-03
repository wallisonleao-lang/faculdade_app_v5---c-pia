from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Literal

from core.models import Course, Exam, ClassSession, Task


Kind = Literal["AULA", "REVISAO_P1", "REVISAO_P2", "TAREFA"]


@dataclass
class DashboardItem:
    kind: Kind
    title: str
    course: str
    target_date: Optional[date]
    score: int
    reason: str
    source_id: Optional[int] = None            # p/ revisões: course.id | p/ tarefa/aula: id do item
    pending_count: int = 0                     # p/ revisões
    pending_classes: List[dict] = field(default_factory=list)  # [{"id": 123, "label": "Aula 3 – ..."}]


def _days_until(d: Optional[date], today: date) -> Optional[int]:
    if not d:
        return None
    return (d - today).days


def _bonus_by_proximity(days: Optional[int]) -> int:
    # quanto mais perto, maior o bônus (máx 30)
    if days is None:
        return 0
    return max(0, 30 - days)


def _proximity_progress(days: Optional[int]) -> int:
    """
    Progressão 0..60:
    - Sem prova: 0
    - >=60 dias: 0
    - 30 dias: 30
    - 14 dias: 46
    - 7 dias: 53
    - 0 dia: 60
    """
    if days is None or days < 0:
        return 0
    return max(0, 60 - min(days, 60))


def _next_exam_date(today: date, course: Course, exam_type: str, exam_qs) -> Optional[date]:
    e = (
        exam_qs
        .filter(course=course, type=exam_type, date__gte=today)
        .order_by("date")
        .first()
    )
    return e.date if e else None


def _format_class(c: ClassSession) -> str:
    if getattr(c, "class_number", None):
        return f"Aula {c.class_number} – {c.title}"
    return f"Aula – {c.title}"


def compute_dashboard_items(
    today: Optional[date] = None,
    limit: Optional[int] = 20,
    *,
    user=None,
) -> List[DashboardItem]:
    today = today or date.today()
    items: List[DashboardItem] = []

    course_qs = Course.objects.all()
    class_qs = ClassSession.objects.select_related("course")
    task_qs = Task.objects.select_related("course")
    exam_qs = Exam.objects
    if user:
        course_qs = course_qs.filter(user=user)
        class_qs = class_qs.filter(course__user=user)
        task_qs = task_qs.filter(course__user=user)
        exam_qs = exam_qs.filter(course__user=user)

    # 1) Aulas atrasadas (data passada e não assistida)
    for c in class_qs.all():
        if c.date and c.date < today and not c.watched:
            days_late = (today - c.date).days
            score = 170 + min(30, days_late)  # atrasado pesa muito
            items.append(
                DashboardItem(
                    kind="AULA",
                    title=f"Assistir: {c.title}",
                    course=str(c.course),
                    target_date=c.date,
                    score=score,
                    reason="Aula atrasada (não assistida)",
                    source_id=c.id,
                )
            )

    # 2) Revisões — aparece APENAS 1 (P1 OU P2) por disciplina
    for course in course_qs.all():
        # Pendências (counts)
        pending_p1 = ClassSession.objects.filter(course=course, watched=True, reviewed_p1=False).count()
        pending_p2 = ClassSession.objects.filter(course=course, watched=True, reviewed_p2=False).count()

        # Listas completas (SEM LIMITES) — para botões individuais no dashboard
        pending_p1_classes = list(
            ClassSession.objects
            .filter(course=course, watched=True, reviewed_p1=False)
            .order_by("date", "class_number", "title")
        )
        pending_p2_classes = list(
            ClassSession.objects
            .filter(course=course, watched=True, reviewed_p2=False)
            .order_by("date", "class_number", "title")
        )
        pending_tasks = list(
            task_qs
            .filter(course=course)
            .exclude(status="DONE")
            .order_by("due_date", "good_by", "title")
        )

        # Para reason (textão) e botões individuais
        p1_class_labels = [_format_class(c) for c in pending_p1_classes]
        p2_class_labels = [_format_class(c) for c in pending_p2_classes]
        task_labels = [t.title for t in pending_tasks]

        p1_pending_list = [{"id": c.id, "label": _format_class(c)} for c in pending_p1_classes]
        p2_pending_list = [{"id": c.id, "label": _format_class(c)} for c in pending_p2_classes]

        # Datas das provas (se houver)
        p1_date = _next_exam_date(today, course, "P1", exam_qs)
        p2_date = _next_exam_date(today, course, "P2", exam_qs)

        p1_days = _days_until(p1_date, today) if p1_date else None
        p2_days = _days_until(p2_date, today) if p2_date else None

        # Score base sempre existente
        base_always = 10

        # Bônus por pendência
        pend_bonus_p1 = min(40, pending_p1 * 2)
        pend_bonus_p2 = min(40, pending_p2 * 2)

        # Bônus por proximidade
        prox_bonus_p1 = _proximity_progress(p1_days)
        prox_bonus_p2 = _proximity_progress(p2_days)

        # Extra na semana da prova
        week_boost_p1 = 15 if (p1_days is not None and 0 <= p1_days <= 7) else 0
        week_boost_p2 = 15 if (p2_days is not None and 0 <= p2_days <= 7) else 0

        p1_score = base_always + pend_bonus_p1 + prox_bonus_p1 + week_boost_p1
        p2_score = base_always + pend_bonus_p2 + prox_bonus_p2 + week_boost_p2

        # Reason (SEM LIMITES) — inclui aulas e tarefas
        p1_details_parts = []
        if p1_class_labels:
            p1_details_parts.append("Aulas: " + "; ".join(p1_class_labels))
        if task_labels:
            p1_details_parts.append("Tarefas: " + "; ".join(task_labels))
        p1_details_text = (" | " + " | ".join(p1_details_parts)) if p1_details_parts else ""

        p2_details_parts = []
        if p2_class_labels:
            p2_details_parts.append("Aulas: " + "; ".join(p2_class_labels))
        if task_labels:
            p2_details_parts.append("Tarefas: " + "; ".join(task_labels))
        p2_details_text = (" | " + " | ".join(p2_details_parts)) if p2_details_parts else ""

        if p1_date:
            p1_reason = f"P1 em {p1_days} dia(s) • {pending_p1} pendente{p1_details_text}"
            p1_target = p1_date
        else:
            p1_reason = f"P1 sem data • {pending_p1} pendente{p1_details_text}"
            p1_target = None

        if p2_date:
            p2_reason = f"P2 em {p2_days} dia(s) • {pending_p2} pendente{p2_details_text}"
            p2_target = p2_date
        else:
            p2_reason = f"P2 sem data • {pending_p2} pendente{p2_details_text}"
            p2_target = None

        # ========= Escolher APENAS 1 revisão por disciplina =========
        # Regra:
        # - Se existir P1 e P2 futuros com data: mostra a prova mais próxima.
        # - Se só uma tiver data futura: mostra essa.
        # - Se nenhuma tiver data: mostra a que tiver pendência; se ambas, preferimos P1.
        chosen_kind: Kind = "REVISAO_P1"

        if p1_target and p2_target:
            chosen_kind = "REVISAO_P1" if p1_target <= p2_target else "REVISAO_P2"
        elif p1_target:
            chosen_kind = "REVISAO_P1"
        elif p2_target:
            chosen_kind = "REVISAO_P2"
        else:
            if pending_p1 > 0 and pending_p2 == 0:
                chosen_kind = "REVISAO_P1"
            elif pending_p2 > 0 and pending_p1 == 0:
                chosen_kind = "REVISAO_P2"
            else:
                chosen_kind = "REVISAO_P1"

        if chosen_kind == "REVISAO_P1":
            items.append(
                DashboardItem(
                    kind="REVISAO_P1",
                    title="Revisão P1",
                    course=str(course),
                    target_date=p1_target,
                    score=p1_score,
                    reason=p1_reason,
                    source_id=course.id,
                    pending_count=pending_p1,
                    pending_classes=p1_pending_list,
                )
            )
        else:
            items.append(
                DashboardItem(
                    kind="REVISAO_P2",
                    title="Revisão P2",
                    course=str(course),
                    target_date=p2_target,
                    score=p2_score,
                    reason=p2_reason,
                    source_id=course.id,
                    pending_count=pending_p2,
                    pending_classes=p2_pending_list,
                )
            )

    # 3) Tarefas (bom para / entrega)
    for t in task_qs.all():
        if t.status == "DONE":
            continue

        actual_due = t.due_date or t.good_by
        target = actual_due or today
        days = _days_until(target, today)

        score = 0
        reason = ""

        if actual_due is not None and days == 0:
            score += 230  # sempre acima de qualquer aula, inclusive atrasadas
            reason = "Entrega hoje"
        elif days is not None and days < 0:
            score += 100
            reason = "Tarefa atrasada"
        elif days is not None and days <= 2:
            score += 80
            reason = "Entrega/bom para muito próximo"
        elif days is not None and days <= 7:
            score += 50
            reason = "Entrega/bom para nesta semana"
        else:
            score += 20
            reason = "Tarefa pendente"

        score += _bonus_by_proximity(days)

        items.append(
            DashboardItem(
                kind="TAREFA",
                title=t.title,
                course=str(t.course),
                target_date=target if target != today else None,
                score=score,
                reason=reason,
                source_id=t.id,
            )
        )

    items.sort(key=lambda x: x.score, reverse=True)
    return items[:limit] if limit else items
