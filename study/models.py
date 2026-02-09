from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import Course


class StudyPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_plans")
    name = models.CharField("Nome", max_length=120)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_plans",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("user", "name")]

    def __str__(self) -> str:
        return self.name


class StudyTag(models.Model):
    area = models.CharField("Área", max_length=80)
    tema = models.CharField("Tema", max_length=80)
    subtema = models.CharField("Subtema", max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["area", "tema", "subtema"]
        unique_together = [("area", "tema", "subtema")]

    def __str__(self) -> str:
        return f"{self.area} / {self.tema} / {self.subtema}"


class StudySource(models.Model):
    instituicao = models.CharField("Instituição", max_length=120)
    prova_nome = models.CharField("Prova", max_length=120)
    ano = models.PositiveIntegerField("Ano", null=True, blank=True)
    pdf_file = models.FileField("PDF", upload_to="study/sources/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ano", "instituicao", "prova_nome"]

    def __str__(self) -> str:
        year = f" {self.ano}" if self.ano else ""
        return f"{self.instituicao} - {self.prova_nome}{year}"


class StudyQuestion(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "EASY", "Fácil"
        MEDIUM = "MEDIUM", "Média"
        HARD = "HARD", "Difícil"

    class Choice(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"
        E = "E", "E"

    tag = models.ForeignKey(StudyTag, on_delete=models.PROTECT, related_name="questions")
    source = models.ForeignKey(
        StudySource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )

    enunciado = models.TextField("Enunciado")
    choice_a = models.CharField("Alternativa A", max_length=240)
    choice_b = models.CharField("Alternativa B", max_length=240)
    choice_c = models.CharField("Alternativa C", max_length=240)
    choice_d = models.CharField("Alternativa D", max_length=240)
    choice_e = models.CharField("Alternativa E", max_length=240)
    correct_choice = models.CharField("Correta", max_length=1, choices=Choice.choices)
    explanation = models.TextField("Comentário", blank=True)

    difficulty = models.CharField("Dificuldade", max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    source_page = models.PositiveIntegerField("Página", null=True, blank=True)
    source_snippet = models.CharField("Trecho", max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tag__area", "tag__tema", "tag__subtema", "id"]

    def __str__(self) -> str:
        return f"{self.tag} - Q{self.id}"


class StudySession(models.Model):
    class Mode(models.TextChoices):
        BLOCK = "BLOCK", "Bloco"
        REVIEW = "REVIEW", "Revisão"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_sessions")
    plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )
    mode = models.CharField("Modo", max_length=10, choices=Mode.choices, default=Mode.BLOCK)
    planned_questions = models.PositiveIntegerField("Questões planejadas")
    target_minutes = models.PositiveIntegerField("Tempo alvo (min)", null=True, blank=True)
    recommended_tag = models.ForeignKey(
        StudyTag,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommended_sessions",
    )
    started_at = models.DateTimeField("Início", default=timezone.now)
    ended_at = models.DateTimeField("Fim", null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Sessão {self.id} ({self.get_mode_display()})"


class StudySessionItem(models.Model):
    class Choice(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"
        E = "E", "E"

    session = models.ForeignKey(StudySession, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(StudyQuestion, on_delete=models.CASCADE, related_name="session_items")
    order = models.PositiveIntegerField("Ordem")
    user_answer = models.CharField("Resposta", max_length=1, choices=Choice.choices, blank=True)
    is_correct = models.BooleanField("Acertou?", null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField("Tempo (segundos)", null=True, blank=True)
    flagged_review = models.BooleanField("Revisar depois", default=False)

    class Meta:
        ordering = ["order"]
        unique_together = [("session", "order"), ("session", "question")]

    def __str__(self) -> str:
        return f"Sessão {self.session_id} - Q{self.question_id}"


class StudyErrorLog(models.Model):
    class Reason(models.TextChoices):
        CONTEUDO = "CONTEUDO", "Conteúdo"
        INTERPRETACAO = "INTERPRETACAO", "Interpretação"
        PEGADINHA = "PEGADINHA", "Pegadinha"
        PRESSA = "PRESSA", "Pressa"
        ESQUECI_REGRA = "ESQUECI_REGRA", "Esqueci regra"
        CONFUSAO_DIAG = "CONFUSAO_DIAG", "Confusão diagnóstica"
        OUTRO = "OUTRO", "Outro"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_error_logs")
    question = models.ForeignKey(StudyQuestion, on_delete=models.CASCADE, related_name="error_logs")
    session_item = models.ForeignKey(
        StudySessionItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="error_logs",
    )
    error_reason = models.CharField("Motivo", max_length=20, choices=Reason.choices)
    rule_of_thumb = models.CharField("Regra de bolso", max_length=200)
    note = models.CharField("Nota", max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Erro Q{self.question_id} ({self.get_error_reason_display()})"


class StudyReviewSchedule(models.Model):
    class Stage(models.IntegerChoices):
        STAGE_1 = 1, "24h"
        STAGE_2 = 2, "7d"
        STAGE_3 = 3, "30d"

    class Result(models.TextChoices):
        CORRECT = "CORRECT", "Acerto"
        INCORRECT = "INCORRECT", "Erro"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="study_reviews")
    question = models.ForeignKey(StudyQuestion, on_delete=models.CASCADE, related_name="review_schedules")
    stage = models.IntegerField("Etapa", choices=Stage.choices, default=Stage.STAGE_1)
    due_at = models.DateTimeField("Vence em")
    last_result = models.CharField("Último resultado", max_length=10, choices=Result.choices, blank=True)
    active = models.BooleanField("Ativo", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at"]
        indexes = [
            models.Index(fields=["user", "active", "due_at"]),
            models.Index(fields=["question", "active"]),
        ]
        unique_together = [("user", "question")]

    def __str__(self) -> str:
        return f"Review Q{self.question_id} (stage {self.stage})"
