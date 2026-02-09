from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from study.models import StudyErrorLog, StudyQuestion, StudyReviewSchedule


REVIEW_DELAYS = {
    1: timedelta(hours=24),
    2: timedelta(days=7),
    3: timedelta(days=30),
}


def schedule_from_error(user, question: StudyQuestion, session_item=None) -> StudyReviewSchedule:
    due_at = timezone.now() + REVIEW_DELAYS[1]
    defaults = {
        "stage": StudyReviewSchedule.Stage.STAGE_1,
        "due_at": due_at,
        "active": True,
        "last_result": StudyReviewSchedule.Result.INCORRECT,
    }
    with transaction.atomic():
        schedule, created = StudyReviewSchedule.objects.select_for_update().get_or_create(
            user=user,
            question=question,
            defaults=defaults,
        )
        if not created:
            schedule.stage = StudyReviewSchedule.Stage.STAGE_1
            schedule.due_at = due_at
            schedule.active = True
            schedule.last_result = StudyReviewSchedule.Result.INCORRECT
            schedule.save(update_fields=["stage", "due_at", "active", "last_result", "updated_at"])
    return schedule


def due_reviews_qs(user):
    now = timezone.now()
    return StudyReviewSchedule.objects.filter(user=user, active=True, due_at__lte=now).order_by("due_at")


def last_error_log_for_question(user, question: StudyQuestion) -> StudyErrorLog | None:
    return (
        StudyErrorLog.objects
        .filter(user=user, question=question)
        .order_by("-created_at")
        .first()
    )


def select_similar_question(question: StudyQuestion) -> StudyQuestion:
    base_qs = StudyQuestion.objects.select_related("tag")
    tag = question.tag
    if not tag:
        return question

    same_subtema = base_qs.filter(tag__area=tag.area, tag__tema=tag.tema, tag__subtema=tag.subtema).exclude(id=question.id)
    if same_subtema.exists():
        return same_subtema.order_by("?").first()

    same_tema = base_qs.filter(tag__area=tag.area, tag__tema=tag.tema).exclude(id=question.id)
    if same_tema.exists():
        return same_tema.order_by("?").first()

    return question


def apply_review_result(user, question: StudyQuestion, is_correct: bool) -> tuple[StudyReviewSchedule, bool]:
    now = timezone.now()
    with transaction.atomic():
        schedule = StudyReviewSchedule.objects.select_for_update().get(user=user, question=question)

        if is_correct:
            if schedule.stage == StudyReviewSchedule.Stage.STAGE_1:
                schedule.stage = StudyReviewSchedule.Stage.STAGE_2
                schedule.due_at = now + REVIEW_DELAYS[2]
                schedule.active = True
            elif schedule.stage == StudyReviewSchedule.Stage.STAGE_2:
                schedule.stage = StudyReviewSchedule.Stage.STAGE_3
                schedule.due_at = now + REVIEW_DELAYS[3]
                schedule.active = True
            else:
                schedule.active = False
            schedule.last_result = StudyReviewSchedule.Result.CORRECT
        else:
            schedule.stage = StudyReviewSchedule.Stage.STAGE_1
            schedule.due_at = now + REVIEW_DELAYS[1]
            schedule.active = True
            schedule.last_result = StudyReviewSchedule.Result.INCORRECT

        schedule.save(update_fields=["stage", "due_at", "active", "last_result", "updated_at"])
    return schedule, not schedule.active
