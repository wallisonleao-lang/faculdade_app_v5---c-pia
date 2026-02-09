from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from hospital_game.models import Department, DailyLedger, HospitalProfile, UserDepartment, UserPatientCard
from hospital_game.services.claim_service import claim_daily
from hospital_game.services.upgrade_service import finish_upgrade, start_upgrade


def _get_or_create_profile(user) -> HospitalProfile:
    profile, _ = HospitalProfile.objects.get_or_create(user=user)
    return profile


def _get_or_create_today_ledger(user) -> DailyLedger:
    today = timezone.localdate()
    ledger, _ = DailyLedger.objects.get_or_create(user=user, date=today)
    return ledger


def _serialize_department(user_department: UserDepartment, now):
    department = user_department.department
    next_level = user_department.level + 1
    return {
        "key": department.key,
        "label": department.label,
        "level": user_department.level,
        "max_level": department.max_level,
        "upgrade_ends_at": user_department.upgrade_ends_at.isoformat() if user_department.upgrade_ends_at else None,
        "can_finish": bool(user_department.upgrade_ends_at and now >= user_department.upgrade_ends_at),
        "cost_energy": department.base_cost_energy * next_level,
        "cost_supplies": department.base_cost_supplies * next_level,
        "duration_seconds": department.base_upgrade_seconds * next_level,
    }


@login_required
def hospital_dashboard(request):
    return render(request, "hospital_game/dashboard.html")


@login_required
def collection_view(request):
    cards = (
        UserPatientCard.objects.filter(user=request.user)
        .select_related("card")
        .order_by("card__rarity", "card__title")
    )
    return render(request, "hospital_game/collection.html", {"cards": cards})


@login_required
@require_GET
def api_status(request):
    profile = _get_or_create_profile(request.user)
    ledger = _get_or_create_today_ledger(request.user)
    now = timezone.now()

    departments = []
    for department in Department.objects.filter(is_active=True):
        user_department, _ = UserDepartment.objects.get_or_create(user=request.user, department=department)
        departments.append(_serialize_department(user_department, now))

    data = {
        "profile": {
            "energy_total": profile.energy_total,
            "supplies_total": profile.supplies_total,
            "reputation_total": profile.reputation_total,
            "last_daily_claim_at": profile.last_daily_claim_at.isoformat() if profile.last_daily_claim_at else None,
        },
        "ledger": {
            "date": str(ledger.date),
            "energy_earned": ledger.energy_earned,
            "supplies_earned": ledger.supplies_earned,
            "tasks_completed_count": ledger.tasks_completed_count,
            "daily_claimed": ledger.daily_claimed,
        },
        "departments": departments,
        "server_time": now.isoformat(),
    }
    return JsonResponse(data)


@login_required
@require_POST
def api_claim(request):
    result = claim_daily(request.user)
    if result.status == "invalid":
        return JsonResponse({"message": result.message}, status=400)
    if result.status == "already_claimed":
        return JsonResponse({"message": result.message}, status=409)

    payload = {
        "message": result.message,
        "reputation_bonus": result.reputation_bonus,
        "card": None,
    }
    if result.card:
        payload["card"] = {
            "title": result.card.card.title,
            "rarity": result.card.card.rarity,
            "count": result.card.count,
        }
    return JsonResponse(payload)


@login_required
@require_POST
def api_start_upgrade(request, key):
    result = start_upgrade(request.user, key)
    status_map = {
        "not_found": 404,
        "invalid": 400,
        "conflict": 409,
    }
    if result.status in status_map:
        return JsonResponse({"message": result.message}, status=status_map[result.status])
    return JsonResponse({"message": result.message})


@login_required
@require_POST
def api_finish_upgrade(request, key):
    result = finish_upgrade(request.user, key)
    status_map = {
        "not_found": 404,
        "invalid": 400,
        "conflict": 409,
    }
    if result.status in status_map:
        return JsonResponse({"message": result.message}, status=status_map[result.status])
    return JsonResponse({"message": result.message})
