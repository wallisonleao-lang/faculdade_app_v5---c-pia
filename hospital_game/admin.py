from django.contrib import admin

from hospital_game.models import (
    ActivityCompletionLog,
    DailyLedger,
    Department,
    HospitalProfile,
    PatientCard,
    TaskCompletionLog,
    UserDepartment,
    UserPatientCard,
)


@admin.register(HospitalProfile)
class HospitalProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "energy_total", "supplies_total", "reputation_total", "last_daily_claim_at")
    search_fields = ("user__email", "user__username")


@admin.register(DailyLedger)
class DailyLedgerAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "date",
        "energy_earned",
        "supplies_earned",
        "tasks_completed_count",
        "daily_claimed",
    )
    list_filter = ("daily_claimed", "date")
    search_fields = ("user__email", "user__username")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "label",
        "base_upgrade_seconds",
        "base_cost_energy",
        "base_cost_supplies",
        "max_level",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("key", "label")


@admin.register(UserDepartment)
class UserDepartmentAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "level", "upgrade_ends_at")
    list_filter = ("department",)
    search_fields = ("user__email", "user__username")


@admin.register(PatientCard)
class PatientCardAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "rarity")
    list_filter = ("rarity",)
    search_fields = ("key", "title")


@admin.register(UserPatientCard)
class UserPatientCardAdmin(admin.ModelAdmin):
    list_display = ("user", "card", "count")
    list_filter = ("card__rarity",)
    search_fields = ("user__email", "user__username", "card__title")


@admin.register(TaskCompletionLog)
class TaskCompletionLogAdmin(admin.ModelAdmin):
    list_display = ("task_id", "user", "created_at")
    search_fields = ("task_id", "user__email", "user__username")


@admin.register(ActivityCompletionLog)
class ActivityCompletionLogAdmin(admin.ModelAdmin):
    list_display = ("kind", "object_id", "user", "created_at")
    list_filter = ("kind",)
    search_fields = ("object_id", "user__email", "user__username")
