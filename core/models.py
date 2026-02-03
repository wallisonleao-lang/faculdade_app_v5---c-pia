from django.conf import settings
from django.db import models


class Institution(models.Model):
    name = models.CharField("Instituição", max_length=200, unique=True)
    slug = models.SlugField("Slug", max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class InstitutionCourse(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="courses")
    code = models.CharField("Código", max_length=30, blank=True)
    name = models.CharField("Nome", max_length=200)
    term = models.CharField("Período", max_length=20, blank=True)  # ex: 2026-1
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("institution", "code", "term", "name")]

    def __str__(self):
        label = f"{self.code} - {self.name}" if self.code else self.name
        return f"{self.institution} · {label}"


class InstitutionClass(models.Model):
    institution_course = models.ForeignKey(
        InstitutionCourse,
        on_delete=models.CASCADE,
        related_name="classes",
    )
    title = models.CharField("Título", max_length=200)
    class_number = models.PositiveIntegerField("Número da aula", null=True, blank=True)
    date = models.DateField("Data")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "class_number", "title"]
        unique_together = [("institution_course", "title", "class_number", "date")]

    def __str__(self):
        prefix = f"Aula {self.class_number} - " if self.class_number else ""
        return f"{self.institution_course}: {prefix}{self.title}"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    last_sync_at = models.DateTimeField("Última sincronização", null=True, blank=True)
    auto_sync_master_classes = models.BooleanField("Espelhamento automático de aulas", default=False)
    has_seen_wizard = models.BooleanField("Viu o guia inicial", default=False)

    def __str__(self):
        return f"Perfil de {self.user}"


class FeatureFlag(models.Model):
    key = models.SlugField("Chave", max_length=40, unique=True)
    label = models.CharField("Nome", max_length=120)
    is_enabled = models.BooleanField("Ativo", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        status = "on" if self.is_enabled else "off"
        return f"{self.key} ({status})"


class Course(models.Model):
    class Status(models.TextChoices):
        CURSANDO = "CURSANDO", "Cursando"
        CONCLUIDA = "CONCLUIDA", "Concluída"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses",
        null=True,
        blank=True,
    )
    institution_course = models.ForeignKey(
        InstitutionCourse,
        on_delete=models.SET_NULL,
        related_name="user_courses",
        null=True,
        blank=True,
    )
    code = models.CharField("Código", max_length=30, blank=True)
    name = models.CharField("Nome", max_length=200)
    term = models.CharField("Período", max_length=20, blank=True)  # ex: 2026-1
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.CURSANDO)
    absences_count = models.PositiveIntegerField("Faltas", default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}" if self.code else self.name


class Exam(models.Model):
    class Type(models.TextChoices):
        P1 = "P1", "P1"
        P2 = "P2", "P2"
        OUTRO = "OUTRO", "Outro"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="exams")
    type = models.CharField("Tipo", max_length=10, choices=Type.choices)
    date = models.DateField("Data")

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.course} - {self.type} ({self.date})"


class ClassSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="classes")
    institution_class = models.ForeignKey(
        InstitutionClass,
        on_delete=models.SET_NULL,
        related_name="user_classes",
        null=True,
        blank=True,
    )
    title = models.CharField("Título", max_length=200)
    class_number = models.PositiveIntegerField("Número da aula", null=True, blank=True)
    date = models.DateField("Data")

    watched = models.BooleanField("Assistida", default=False)
    reviewed_p1 = models.BooleanField("Revisada P1", default=False)
    reviewed_p2 = models.BooleanField("Revisada P2", default=False)

    class Meta:
        ordering = ["date", "class_number", "title"]

    def __str__(self):
        prefix = f"Aula {self.class_number} - " if self.class_number else ""
        return f"{self.course}: {prefix}{self.title}"


class Task(models.Model):
    class Type(models.TextChoices):
        LISTA = "LISTA", "Lista/Exercícios"
        TRABALHO = "TRABALHO", "Trabalho"
        LEITURA = "LEITURA", "Leitura"
        OUTRO = "OUTRO", "Outro"

    class Status(models.TextChoices):
        TODO = "TODO", "A fazer"
        DOING = "DOING", "Fazendo"
        DONE = "DONE", "Concluída"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField("Título", max_length=200)
    type = models.CharField("Tipo", max_length=20, choices=Type.choices, default=Type.OUTRO)

    good_by = models.DateField("Bom para", null=True, blank=True)
    due_date = models.DateField("Entrega", null=True, blank=True)

    status = models.CharField("Status", max_length=10, choices=Status.choices, default=Status.TODO)
    done_at = models.DateTimeField("Concluída em", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["status", "due_date", "good_by", "title"]

    def __str__(self):
        return f"{self.course}: {self.title}"


class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="questions")
    classes = models.ManyToManyField(
        ClassSession,
        blank=True,
        related_name="questions",
        verbose_name="Aulas",
    )
    title = models.CharField("Questão", max_length=200)
    topic = models.CharField("Tema", max_length=100, blank=True)
    resolution = models.TextField("Resolução", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["course", "topic", "title"]

    def __str__(self):
        return f"{self.course}: {self.title}"


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField("Alternativa", max_length=200)
    is_correct = models.BooleanField("Correta?", default=False)

    class Meta:
        ordering = ["question", "id"]

    def __str__(self):
        return f"{self.question}: {self.text}"


class QuestionAttempt(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="attempts")
    selected_option = models.ForeignKey(
        QuestionOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempts",
    )
    is_correct = models.BooleanField("Acertou?")
    time_seconds = models.PositiveIntegerField("Tempo (segundos)", null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-attempted_at"]

    def __str__(self):
        status = "Acerto" if self.is_correct else "Erro"
        return f"{self.question} - {status}"
