from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from hospital_game.models import DailyLedger, TaskCompletionLog


@dataclass
class RecordResult:
    created: bool
    ledger: DailyLedger | None
    reason: str | None = None


def _get_task_user(task):
    user = getattr(task, "user", None)
    if user:
        return user
    course = getattr(task, "course", None)
    if course:
        return getattr(course, "user", None)
    return None


def _get_task_difficulty(task) -> int:
    difficulty = getattr(task, "difficulty", None)
    try:
        value = int(difficulty) if difficulty is not None else 1
    except (TypeError, ValueError):
        value = 1
    return max(value, 1)


def _get_task_estimated_minutes(task) -> int:
    estimated = getattr(task, "estimated_minutes", None)
    try:
        value = int(estimated) if estimated is not None else 10
    except (TypeError, ValueError):
        value = 10
    return max(value, 0)


def record_task_completion(task, completed_at=None) -> RecordResult:
    """
    Register a task completion into today's ledger with idempotency.

    Defensive: Task model may not have difficulty/estimated_minutes.
    """
    user = _get_task_user(task)
    if not user:
        return RecordResult(created=False, ledger=None, reason="task_user_missing")

    completed_at = completed_at or timezone.now()
    ledger_date = timezone.localdate(completed_at)
    energy_gain = 5 * _get_task_difficulty(task)
    supplies_gain = int(round(_get_task_estimated_minutes(task) / 10))

    with transaction.atomic():
        log, created = TaskCompletionLog.objects.get_or_create(task_id=task.id, defaults={"user": user})
        if not created:
            return RecordResult(created=False, ledger=None, reason="already_recorded")

        try:
            ledger = DailyLedger.objects.select_for_update().get(user=user, date=ledger_date)
        except DailyLedger.DoesNotExist:
            ledger = DailyLedger.objects.create(user=user, date=ledger_date)

        ledger.energy_earned += energy_gain
        ledger.supplies_earned += supplies_gain
        ledger.tasks_completed_count += 1
        ledger.save(update_fields=["energy_earned", "supplies_earned", "tasks_completed_count"])

    return RecordResult(created=True, ledger=ledger)
