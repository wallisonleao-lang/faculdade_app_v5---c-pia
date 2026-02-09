from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from hospital_game.models import Department, HospitalProfile, UserDepartment


@dataclass
class UpgradeResult:
    status: str
    message: str
    department: Department | None = None
    user_department: UserDepartment | None = None


def _get_or_create_profile(user) -> HospitalProfile:
    profile, _ = HospitalProfile.objects.get_or_create(user=user)
    return profile


def start_upgrade(user, department_key: str) -> UpgradeResult:
    now = timezone.now()

    try:
        department = Department.objects.get(key=department_key, is_active=True)
    except Department.DoesNotExist:
        return UpgradeResult(status="not_found", message="Setor não encontrado.")

    with transaction.atomic():
        profile = HospitalProfile.objects.select_for_update().filter(user=user).first()
        if not profile:
            profile = _get_or_create_profile(user)
            profile = HospitalProfile.objects.select_for_update().get(user=user)

        user_department, _ = UserDepartment.objects.select_for_update().get_or_create(
            user=user, department=department
        )

        if user_department.upgrade_ends_at:
            if now < user_department.upgrade_ends_at:
                return UpgradeResult(
                    status="conflict",
                    message="Este setor já está em melhoria.",
                    department=department,
                    user_department=user_department,
                )
            return UpgradeResult(
                status="conflict",
                message="Melhoria pronta para concluir. Finalize antes de iniciar outra.",
                department=department,
                user_department=user_department,
            )

        if user_department.level >= department.max_level:
            return UpgradeResult(
                status="invalid",
                message="Setor já está no nível máximo.",
                department=department,
                user_department=user_department,
            )

        next_level = user_department.level + 1
        cost_energy = department.base_cost_energy * next_level
        cost_supplies = department.base_cost_supplies * next_level
        duration_seconds = department.base_upgrade_seconds * next_level

        if profile.energy_total < cost_energy or profile.supplies_total < cost_supplies:
            return UpgradeResult(
                status="invalid",
                message="Recursos insuficientes para iniciar a melhoria.",
                department=department,
                user_department=user_department,
            )

        profile.energy_total -= cost_energy
        profile.supplies_total -= cost_supplies
        profile.save(update_fields=["energy_total", "supplies_total"])

        user_department.upgrade_ends_at = now + timedelta(seconds=duration_seconds)
        user_department.save(update_fields=["upgrade_ends_at"])

    return UpgradeResult(
        status="started",
        message="Melhoria iniciada com sucesso.",
        department=department,
        user_department=user_department,
    )


def finish_upgrade(user, department_key: str) -> UpgradeResult:
    now = timezone.now()

    try:
        department = Department.objects.get(key=department_key, is_active=True)
    except Department.DoesNotExist:
        return UpgradeResult(status="not_found", message="Setor não encontrado.")

    with transaction.atomic():
        user_department, _ = UserDepartment.objects.select_for_update().get_or_create(
            user=user, department=department
        )

        if not user_department.upgrade_ends_at:
            return UpgradeResult(
                status="invalid",
                message="Nenhuma melhoria em andamento.",
                department=department,
                user_department=user_department,
            )

        if now < user_department.upgrade_ends_at:
            return UpgradeResult(
                status="conflict",
                message="Melhoria ainda em andamento.",
                department=department,
                user_department=user_department,
            )

        if user_department.level >= department.max_level:
            return UpgradeResult(
                status="invalid",
                message="Setor já está no nível máximo.",
                department=department,
                user_department=user_department,
            )

        user_department.level += 1
        user_department.upgrade_ends_at = None
        user_department.save(update_fields=["level", "upgrade_ends_at"])

    return UpgradeResult(
        status="finished",
        message="Melhoria concluída com sucesso.",
        department=department,
        user_department=user_department,
    )
