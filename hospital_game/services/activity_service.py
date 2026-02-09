from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from hospital_game.models import ActivityCompletionLog, DailyLedger


@dataclass
class ActivityRecordResult:
    created: bool
    ledger: DailyLedger | None
    reason: str | None = None


def record_activity_completion(user, kind: str, object_id: int, completed_at=None) -> ActivityRecordResult:
    """
    Register a class/review completion into today's ledger with idempotency.

    Uses default gains (energy +5, supplies +1) to keep MVP rules consistent.
    """
    completed_at = completed_at or timezone.now()
    ledger_date = timezone.localdate(completed_at)

    energy_gain = 5
    supplies_gain = 1

    with transaction.atomic():
        log, created = ActivityCompletionLog.objects.get_or_create(
            user=user,
            kind=kind,
            object_id=object_id,
        )
        if not created:
            return ActivityRecordResult(created=False, ledger=None, reason="already_recorded")

        ledger, _ = DailyLedger.objects.select_for_update().get_or_create(user=user, date=ledger_date)
        ledger.energy_earned += energy_gain
        ledger.supplies_earned += supplies_gain
        ledger.tasks_completed_count += 1
        ledger.save(update_fields=["energy_earned", "supplies_earned", "tasks_completed_count"])

    return ActivityRecordResult(created=True, ledger=ledger)
