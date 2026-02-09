from django.contrib import admin

from .models import (
    StudyPlan,
    StudyTag,
    StudySource,
    StudyQuestion,
    StudySession,
    StudySessionItem,
    StudyErrorLog,
    StudyReviewSchedule,
)


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "course", "created_at")
    search_fields = ("name", "user__email")
    list_filter = ("created_at",)


@admin.register(StudyTag)
class StudyTagAdmin(admin.ModelAdmin):
    list_display = ("area", "tema", "subtema", "created_at")
    search_fields = ("area", "tema", "subtema")
    list_filter = ("area",)


@admin.register(StudySource)
class StudySourceAdmin(admin.ModelAdmin):
    list_display = ("instituicao", "prova_nome", "ano", "created_at")
    search_fields = ("instituicao", "prova_nome")
    list_filter = ("ano", "instituicao")


@admin.register(StudyQuestion)
class StudyQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "tag", "difficulty", "source", "created_at")
    search_fields = ("enunciado", "source_snippet")
    list_filter = ("difficulty", "tag__area", "tag__tema", "tag__subtema")
    raw_id_fields = ("tag", "source", "plan")


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "mode", "planned_questions", "started_at", "ended_at")
    list_filter = ("mode", "started_at")
    search_fields = ("user__email",)


@admin.register(StudySessionItem)
class StudySessionItemAdmin(admin.ModelAdmin):
    list_display = ("session", "question", "order", "is_correct", "time_spent_seconds", "flagged_review")
    list_filter = ("is_correct", "flagged_review")
    raw_id_fields = ("session", "question")


@admin.register(StudyErrorLog)
class StudyErrorLogAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "error_reason", "created_at")
    list_filter = ("error_reason", "created_at")
    search_fields = ("rule_of_thumb", "note")
    raw_id_fields = ("user", "question", "session_item")


@admin.register(StudyReviewSchedule)
class StudyReviewScheduleAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "stage", "due_at", "active", "updated_at")
    list_filter = ("stage", "active")
    search_fields = ("user__email",)
    raw_id_fields = ("user", "question")
