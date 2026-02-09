from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from study.models import StudyErrorLog, StudyQuestion, StudyTag, StudySessionItem


def _recently_answered_question_ids(user, hours=72):
    cutoff = timezone.now() - timedelta(hours=hours)
    return set(
        StudySessionItem.objects
        .filter(session__user=user, session__started_at__gte=cutoff)
        .values_list("question_id", flat=True)
    )


def _top_error_tags(user, days=30, limit=5):
    cutoff = timezone.now() - timedelta(days=days)
    rows = (
        StudyErrorLog.objects
        .filter(user=user, created_at__gte=cutoff)
        .values("question__tag_id")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    tag_ids = [r["question__tag_id"] for r in rows if r["question__tag_id"]][:limit]
    return list(StudyTag.objects.filter(id__in=tag_ids))


def _normalize(values):
    if not values:
        return []
    if isinstance(values, str):
        return [values]
    return [v for v in values if v]


def recommend_block(user, planned_questions=20, *, area=None, tema=None, subtema=None):
    recent_ids = _recently_answered_question_ids(user)

    qs = StudyQuestion.objects.all()
    area_list = _normalize(area)
    tema_list = _normalize(tema)
    subtema_list = _normalize(subtema)

    if area_list:
        qs = qs.filter(tag__area__in=area_list)
    if tema_list:
        qs = qs.filter(tag__tema__in=tema_list)
    if subtema_list:
        qs = qs.filter(tag__subtema__in=subtema_list)
    if recent_ids:
        qs = qs.exclude(id__in=recent_ids)

    if not qs.exists():
        return {"tag": None, "questions": []}

    questions = list(qs.order_by("?")[:planned_questions])
    if len(questions) < planned_questions:
        fallback_qs = StudyQuestion.objects.exclude(id__in=[q.id for q in questions])
        questions += list(fallback_qs.order_by("?")[: max(0, planned_questions - len(questions))])

    recommended_tag = None
    if subtema_list or tema_list or area_list:
        recommended_tag = (
            StudyTag.objects
            .filter(
                area__in=area_list or StudyTag.objects.values_list("area", flat=True).distinct(),
                tema__in=tema_list or StudyTag.objects.values_list("tema", flat=True).distinct(),
                subtema__in=subtema_list or StudyTag.objects.values_list("subtema", flat=True).distinct(),
            )
            .order_by("area", "tema", "subtema")
            .first()
        )

    return {"tag": recommended_tag, "questions": questions}
