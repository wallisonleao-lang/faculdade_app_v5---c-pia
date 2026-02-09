from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from hospital_game.models import DailyLedger, HospitalProfile
from hospital_game.services.cards_service import draw_patient_card


@dataclass
class ClaimResult:
    status: str
    message: str
    ledger: DailyLedger | None = None
    card: object | None = None
    reputation_bonus: int = 0


def _get_or_create_profile(user) -> HospitalProfile:
    profile, _ = HospitalProfile.objects.get_or_create(user=user)
    return profile


def claim_daily(user) -> ClaimResult:
    """Encerrar plantao: transfers today's ledger into totals with idempotency."""
    today = timezone.localdate()
    now = timezone.now()

    with transaction.atomic():
        profile = HospitalProfile.objects.select_for_update().filter(user=user).first()
        if not profile:
            profile = _get_or_create_profile(user)
            profile = HospitalProfile.objects.select_for_update().get(user=user)

        try:
            ledger = DailyLedger.objects.select_for_update().get(user=user, date=today)
        except DailyLedger.DoesNotExist:
            return ClaimResult(status="invalid", message="Conclua ao menos 1 atividade hoje para encerrar o plantão.")

        if ledger.tasks_completed_count < 1:
            return ClaimResult(status="invalid", message="Conclua ao menos 1 atividade para encerrar o plantão.")

        if ledger.daily_claimed:
            return ClaimResult(status="already_claimed", message="Plantão já encerrado hoje.", ledger=ledger)

        profile.energy_total += ledger.energy_earned
        profile.supplies_total += ledger.supplies_earned

        reputation_bonus = 0
        if ledger.tasks_completed_count >= 5:
            reputation_bonus = 5
        elif ledger.tasks_completed_count >= 3:
            reputation_bonus = 2

        if reputation_bonus:
            profile.reputation_total += reputation_bonus

        profile.last_daily_claim_at = now
        profile.save(update_fields=["energy_total", "supplies_total", "reputation_total", "last_daily_claim_at"])

        ledger.daily_claimed = True
        ledger.claimed_at = now
        ledger.save(update_fields=["daily_claimed", "claimed_at"])

        card = draw_patient_card(user)

    return ClaimResult(
        status="claimed",
        message="Plantão encerrado com sucesso.",
        ledger=ledger,
        card=card,
        reputation_bonus=reputation_bonus,
    )
