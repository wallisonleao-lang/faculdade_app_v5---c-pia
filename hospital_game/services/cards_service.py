from __future__ import annotations

import random

from django.db import transaction

from hospital_game.models import PatientCard, UserPatientCard


RARITY_WEIGHTS = (
    ("COMMON", 0.70),
    ("RARE", 0.25),
    ("EPIC", 0.05),
)


def _draw_rarity() -> str:
    roll = random.random()
    cumulative = 0.0
    for rarity, weight in RARITY_WEIGHTS:
        cumulative += weight
        if roll <= cumulative:
            return rarity
    return "COMMON"


def draw_patient_card(user) -> UserPatientCard | None:
    """
    Draws a single patient card for a user and increments its count.
    Returns the UserPatientCard (or None if no cards exist).
    """
    rarity = _draw_rarity()
    cards = list(PatientCard.objects.filter(rarity=rarity))
    if not cards:
        cards = list(PatientCard.objects.all())
    if not cards:
        return None

    card = random.choice(cards)
    with transaction.atomic():
        user_card, _ = UserPatientCard.objects.select_for_update().get_or_create(
            user=user, card=card, defaults={"count": 0}
        )
        user_card.count += 1
        user_card.save(update_fields=["count"])
    return user_card
