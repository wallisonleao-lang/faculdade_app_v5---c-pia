from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class HospitalProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hospital_profile")
    energy_total = models.PositiveIntegerField(default=0)
    supplies_total = models.PositiveIntegerField(default=0)
    reputation_total = models.PositiveIntegerField(default=0)
    last_daily_claim_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["user_id"]

    def __str__(self) -> str:
        return f"HospitalProfile({self.user_id})"


class DailyLedger(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hospital_ledgers")
    date = models.DateField()
    energy_earned = models.PositiveIntegerField(default=0)
    supplies_earned = models.PositiveIntegerField(default=0)
    tasks_completed_count = models.PositiveIntegerField(default=0)
    daily_claimed = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "date")]
        ordering = ["-date", "user_id"]

    def __str__(self) -> str:
        return f"DailyLedger({self.user_id}, {self.date})"


class Department(models.Model):
    class Key(models.TextChoices):
        TRIAGE = "TRIAGE", "Triagem"
        WARD = "WARD", "Enfermaria"
        OR = "OR", "Centro cirúrgico"
        LAB = "LAB", "Laboratório"

    key = models.CharField(max_length=20, choices=Key.choices, unique=True)
    label = models.CharField(max_length=100)
    base_upgrade_seconds = models.PositiveIntegerField(default=60)
    base_cost_energy = models.PositiveIntegerField(default=20)
    base_cost_supplies = models.PositiveIntegerField(default=10)
    max_level = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class UserDepartment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hospital_departments")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="user_departments")
    level = models.PositiveIntegerField(default=0)
    upgrade_ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "department")]
        ordering = ["department__key", "user_id"]

    def __str__(self) -> str:
        return f"{self.user_id} - {self.department.key}"

    @property
    def is_upgrading(self) -> bool:
        if not self.upgrade_ends_at:
            return False
        return timezone.now() < self.upgrade_ends_at


class PatientCard(models.Model):
    class Rarity(models.TextChoices):
        COMMON = "COMMON", "Comum"
        RARE = "RARE", "Rara"
        EPIC = "EPIC", "Épica"

    key = models.SlugField(max_length=60, unique=True)
    title = models.CharField(max_length=120)
    rarity = models.CharField(max_length=10, choices=Rarity.choices)
    flavor_text = models.TextField(blank=True)

    class Meta:
        ordering = ["rarity", "title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.rarity})"


class UserPatientCard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_cards")
    card = models.ForeignKey(PatientCard, on_delete=models.CASCADE, related_name="user_cards")
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("user", "card")]
        ordering = ["card__rarity", "card__title"]

    def __str__(self) -> str:
        return f"{self.user_id} - {self.card.key} x{self.count}"


class TaskCompletionLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_completion_logs")
    task_id = models.PositiveIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"TaskCompletionLog({self.task_id})"


class ActivityCompletionLog(models.Model):
    class Kind(models.TextChoices):
        CLASS_WATCHED = "CLASS_WATCHED", "Aula assistida"
        REVIEW_P1 = "REVIEW_P1", "Revisão P1"
        REVIEW_P2 = "REVIEW_P2", "Revisão P2"
        STUDY_SESSION = "STUDY_SESSION", "Sessão de estudo"
        STUDY_REVIEW = "STUDY_REVIEW", "Revisão de estudo"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_completion_logs")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    object_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "kind", "object_id")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ActivityCompletionLog({self.kind}, {self.object_id})"
