from django.contrib import admin
from .models import (
    Course,
    Exam,
    ClassSession,
    Task,
    Question,
    QuestionAttempt,
    QuestionOption,
    Institution,
    InstitutionCourse,
    InstitutionClass,
    UserProfile,
    FeatureFlag,
)


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")


@admin.register(InstitutionCourse)
class InstitutionCourseAdmin(admin.ModelAdmin):
    list_display = ("institution", "code", "name", "term", "created_at")
    list_filter = ("institution", "term")
    search_fields = ("code", "name")


@admin.register(InstitutionClass)
class InstitutionClassAdmin(admin.ModelAdmin):
    list_display = ("institution_course", "date", "class_number", "title", "updated_at")
    list_filter = ("institution_course",)
    search_fields = ("title",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "institution", "last_sync_at")
    list_filter = ("institution",)
    search_fields = ("user__email", "user__username")


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "is_enabled", "updated_at")
    list_filter = ("is_enabled",)
    search_fields = ("key", "label")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "term", "status", "user", "institution_course")
    list_filter = ("term", "status", "user", "institution_course")
    search_fields = ("code", "name", "user__email", "user__username")


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("course", "type", "date")
    list_filter = ("type", "date")
    search_fields = ("course__name", "course__code")


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "date",
        "class_number",
        "title",
        "watched",
        "reviewed_p1",
        "reviewed_p2",
        "institution_class",
    )
    list_filter = ("course", "watched", "reviewed_p1", "reviewed_p2")
    search_fields = ("title", "course__name", "course__code")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("course", "title", "type", "status", "good_by", "due_date")
    list_filter = ("type", "status", "due_date")
    search_fields = ("title", "course__name", "course__code")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("course", "title", "topic", "created_at")
    list_filter = ("course",)
    search_fields = ("title", "topic", "course__name", "course__code")
    filter_horizontal = ("classes",)


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 3
    min_num = 2


QuestionAdmin.inlines = [QuestionOptionInline]


@admin.register(QuestionAttempt)
class QuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ("question", "selected_option", "is_correct", "time_seconds", "attempted_at")
    list_filter = ("is_correct",)
