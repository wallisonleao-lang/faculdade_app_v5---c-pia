from django import forms
from allauth.account.forms import SignupForm
from django.utils.text import slugify
from .models import (
    Course,
    Exam,
    ClassSession,
    Task,
    Question,
    QuestionAttempt,
    QuestionOption,
    InstitutionCourse,
    Institution,
    UserProfile,
)


def _class_label_without_course(cls: ClassSession) -> str:
    prefix = f"Aula {cls.class_number} - " if cls.class_number else ""
    return f"{prefix}{cls.title}"


class BootstrapModelForm(forms.ModelForm):
    """
    Aplica classes do Bootstrap automaticamente em todos os campos.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            input_type = getattr(field.widget, "input_type", "")
            if input_type == "checkbox":
                field.widget.attrs["class"] = "form-check-input"
            elif input_type == "select":
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


class CourseForm(BootstrapModelForm):
    class Meta:
        model = Course
        fields = ["institution_course", "code", "name", "term", "status"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        institution_field = self.fields.get("institution_course")
        if institution_field:
            if user and hasattr(user, "profile") and user.profile.institution:
                institution_field.queryset = InstitutionCourse.objects.filter(
                    institution=user.profile.institution
                ).order_by("name")
            else:
                institution_field.queryset = InstitutionCourse.objects.none()
            institution_field.required = False


class ExamForm(BootstrapModelForm):
    class Meta:
        model = Exam
        fields = ["course", "type", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["course"].queryset = Course.objects.filter(user=user).order_by("name")


class ClassSessionForm(BootstrapModelForm):
    class Meta:
        model = ClassSession
        fields = ["course", "title", "class_number", "date", "watched", "reviewed_p1", "reviewed_p2"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["course"].queryset = Course.objects.filter(user=user).order_by("name")


class TaskForm(BootstrapModelForm):
    class Meta:
        model = Task
        fields = ["course", "title", "type", "good_by", "due_date", "status"]
        widgets = {
            "good_by": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["course"].queryset = Course.objects.filter(user=user).order_by("name")


class QuestionForm(BootstrapModelForm):
    class Meta:
        model = Question
        fields = ["course", "classes", "title", "topic", "resolution"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["topic"].widget.attrs["list"] = "topic-suggestions"
        classes_field = self.fields.get("classes")
        if user:
            self.fields["course"].queryset = Course.objects.filter(user=user).order_by("name")
        if classes_field:
            classes_field.label_from_instance = _class_label_without_course
            course_id = None
            if self.data.get("course"):
                try:
                    course_id = int(self.data.get("course"))
                except (TypeError, ValueError):
                    course_id = None
            elif getattr(self.instance, "course_id", None):
                course_id = self.instance.course_id

            if course_id:
                classes_field.queryset = ClassSession.objects.filter(course_id=course_id).order_by(
                    "date", "class_number", "title"
                )
            else:
                if user:
                    classes_field.queryset = ClassSession.objects.filter(course__user=user).order_by(
                        "course__name", "date", "class_number", "title"
                    )
                else:
                    classes_field.queryset = ClassSession.objects.all().order_by(
                        "course__name", "date", "class_number", "title"
                    )

    def clean_topic(self):
        value = (self.cleaned_data.get("topic") or "").strip()
        if not value:
            return ""
        tags = [t for t in value.split() if t]
        return " ".join(tags)

    def clean(self):
        cleaned = super().clean()
        course = cleaned.get("course")
        classes = cleaned.get("classes")
        if course and classes:
            invalid = classes.exclude(course=course)
            if invalid.exists():
                self.add_error("classes", "Selecione apenas aulas da disciplina escolhida.")
        return cleaned


class QuestionAttemptForm(BootstrapModelForm):
    class Meta:
        model = QuestionAttempt
        fields = ["question", "selected_option", "is_correct", "time_seconds"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["question"].queryset = Question.objects.filter(course__user=user)


class QuestionImportForm(forms.Form):
    course = forms.ModelChoiceField(queryset=Course.objects.none(), label="Disciplina")
    classes = forms.ModelMultipleChoiceField(
        queryset=ClassSession.objects.none(),
        label="Aulas",
        required=False,
    )
    file = forms.FileField(label="Arquivo CSV", required=False)
    pasted_csv = forms.CharField(
        label="CSV colado",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": "Cole aqui o CSV com cabeçalho"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        course_id = None
        data = args[0] if args else kwargs.get("data")
        initial = kwargs.get("initial", {})
        if data and data.get("course"):
            try:
                course_id = int(data.get("course"))
            except (TypeError, ValueError):
                course_id = None
        elif initial.get("course"):
            try:
                course_id = int(initial.get("course"))
            except (TypeError, ValueError):
                try:
                    course_id = int(initial.get("course").id)
                except (TypeError, ValueError, AttributeError):
                    course_id = None

        super().__init__(*args, **kwargs)
        self.fields["course"].widget.attrs["class"] = "form-select"
        self.fields["classes"].widget.attrs["class"] = "form-select"
        self.fields["classes"].widget.attrs["size"] = "6"
        self.fields["classes"].label_from_instance = _class_label_without_course
        self.fields["file"].widget.attrs["class"] = "form-control"
        self.fields["pasted_csv"].widget.attrs["class"] = "form-control"
        if user:
            self.fields["course"].queryset = Course.objects.filter(user=user).order_by("name")
        if course_id:
            self.fields["classes"].queryset = ClassSession.objects.filter(course_id=course_id).order_by(
                "date", "class_number", "title"
            )

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get("file")
        pasted = (cleaned.get("pasted_csv") or "").strip()
        if not file and not pasted:
            raise forms.ValidationError("Envie um arquivo CSV ou cole o conteúdo.")
        course = cleaned.get("course")
        classes = cleaned.get("classes")
        if course and classes:
            invalid = classes.exclude(course=course)
            if invalid.exists():
                self.add_error("classes", "Selecione apenas aulas da disciplina escolhida.")
        return cleaned


class CustomSignupForm(SignupForm):
    def save(self, request):
        user = super().save(request)
        UserProfile.objects.get_or_create(user=user)
        return user


class InstitutionForm(BootstrapModelForm):
    class Meta:
        model = Institution
        fields = ["name", "slug"]
        labels = {"slug": "ID (ex: fmusp)"}

    def clean_slug(self):
        value = (self.cleaned_data.get("slug") or "").strip()
        if not value:
            name = self.cleaned_data.get("name") or ""
            value = slugify(name)
        return value


class ProfileInstitutionForm(forms.ModelForm):
    institution_code = forms.CharField(
        label="Código da faculdade",
        required=False,
        help_text="Ex.: fmusp",
    )

    class Meta:
        model = UserProfile
        fields = ["institution", "institution_code", "auto_sync_master_classes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institution"].queryset = Institution.objects.all().order_by("name")
        self.fields["institution"].widget.attrs["class"] = "form-select"
        self.fields["auto_sync_master_classes"].widget.attrs["class"] = "form-check-input"
        self.fields["institution_code"].widget.attrs["class"] = "form-control"
        self.fields["institution_code"].widget.attrs["placeholder"] = "fmusp"

    def clean(self):
        cleaned = super().clean()
        code = (cleaned.get("institution_code") or "").strip().lower()
        institution = cleaned.get("institution")
        if code:
            inst_by_code = Institution.objects.filter(slug=code).first()
            if not inst_by_code:
                self.add_error("institution_code", "Código inválido. Verifique com a sua faculdade.")
            else:
                if institution and institution.id != inst_by_code.id:
                    self.add_error("institution", "A faculdade selecionada não corresponde ao código.")
                cleaned["institution"] = inst_by_code
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.institution = self.cleaned_data.get("institution")
        if commit:
            instance.save()
        return instance
