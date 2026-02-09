from __future__ import annotations

from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .services.ledger_service import record_task_completion


Task = apps.get_model("core", "Task")


def _is_task_completed(task) -> bool:
    """
    Detect completion with defensive checks since the Task model may vary.
    """
    if hasattr(task, "completed"):
        return bool(getattr(task, "completed"))
    status = getattr(task, "status", None)
    if status is not None:
        return status == "DONE"
    return False


def _has_completed_timestamp(task) -> bool:
    if hasattr(task, "completed_at"):
        return getattr(task, "completed_at") is not None
    if hasattr(task, "done_at"):
        return getattr(task, "done_at") is not None
    return False


@receiver(post_save, sender=Task)
def record_task_completion_on_save(sender, instance, **kwargs):
    if not _is_task_completed(instance):
        return
    if not _has_completed_timestamp(instance):
        # Prefer timestamped completions to avoid counting draft statuses.
        return
    record_task_completion(instance, completed_at=_get_completed_at(instance))


def _get_completed_at(task):
    if hasattr(task, "completed_at") and task.completed_at:
        return task.completed_at
    if hasattr(task, "done_at") and task.done_at:
        return task.done_at
    return timezone.now()
