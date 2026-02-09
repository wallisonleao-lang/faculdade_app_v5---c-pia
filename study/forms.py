from django import forms

from core.forms import BootstrapModelForm
from .models import (
    StudyErrorLog,
    StudyPlan,
    StudyQuestion,
    StudyTag,
)


class StudySessionStartForm(forms.Form):
    planned_questions = forms.IntegerField(label="Qtd. questões", min_value=5, max_value=50, initial=20)
    target_minutes = forms.IntegerField(label="Tempo alvo (min)", min_value=10, max_value=180, initial=60)
    area = forms.MultipleChoiceField(label="Área", required=False, choices=[])
    tema = forms.MultipleChoiceField(label="Tema", required=False, choices=[])
    subtema = forms.MultipleChoiceField(label="Subtema", required=False, choices=[])
    plan = forms.ModelChoiceField(
        label="Plano de estudo",
        queryset=StudyPlan.objects.none(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["plan"].queryset = StudyPlan.objects.filter(user=user).order_by("name")
        self.fields["area"].choices = [
            (val, val)
            for val in StudyTag.objects.order_by("area").values_list("area", flat=True).distinct()
            if val
        ]
        self.fields["tema"].choices = [
            (val, val)
            for val in StudyTag.objects.order_by("tema").values_list("tema", flat=True).distinct()
            if val
        ]
        self.fields["subtema"].choices = [
            (val, val)
            for val in StudyTag.objects.order_by("subtema").values_list("subtema", flat=True).distinct()
            if val
        ]
        self.fields["planned_questions"].widget.attrs["class"] = "form-control"
        self.fields["target_minutes"].widget.attrs["class"] = "form-control"
        self.fields["area"].widget.attrs["class"] = "form-select"
        self.fields["tema"].widget.attrs["class"] = "form-select"
        self.fields["subtema"].widget.attrs["class"] = "form-select"
        self.fields["area"].widget.attrs["multiple"] = "multiple"
        self.fields["tema"].widget.attrs["multiple"] = "multiple"
        self.fields["subtema"].widget.attrs["multiple"] = "multiple"
        self.fields["area"].widget.attrs["size"] = "4"
        self.fields["tema"].widget.attrs["size"] = "4"
        self.fields["subtema"].widget.attrs["size"] = "4"
        self.fields["plan"].widget.attrs["class"] = "form-select"


class StudyAnswerForm(forms.Form):
    choice = forms.ChoiceField(
        label="Resposta",
        choices=StudyQuestion.Choice.choices,
        widget=forms.RadioSelect,
    )
    time_spent_seconds = forms.IntegerField(
        label="Tempo (segundos)",
        min_value=0,
        required=False,
        widget=forms.HiddenInput,
    )
    flagged_review = forms.BooleanField(label="Revisar depois", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["time_spent_seconds"].widget.attrs["id"] = "time-spent-seconds"


class StudyErrorLogForm(BootstrapModelForm):
    class Meta:
        model = StudyErrorLog
        fields = ["error_reason", "rule_of_thumb", "note"]


class StudyQuestionForm(BootstrapModelForm):
    class Meta:
        model = StudyQuestion
        fields = [
            "tag",
            "source",
            "plan",
            "enunciado",
            "choice_a",
            "choice_b",
            "choice_c",
            "choice_d",
            "choice_e",
            "correct_choice",
            "explanation",
            "difficulty",
            "source_page",
            "source_snippet",
        ]


class StudyQuestionImportForm(forms.Form):
    file = forms.FileField(label="Arquivo CSV", required=False)
    pasted_csv = forms.CharField(
        label="CSV colado",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8, "placeholder": "Cole aqui o CSV com cabeçalho"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].widget.attrs["class"] = "form-control"
        self.fields["pasted_csv"].widget.attrs["class"] = "form-control"


class StudyReviewAnswerForm(forms.Form):
    choice = forms.ChoiceField(
        label="Resposta",
        choices=StudyQuestion.Choice.choices,
        widget=forms.RadioSelect,
    )


class StudyQuestionFilterForm(forms.Form):
    area = forms.MultipleChoiceField(label="Área", required=False, choices=[])
    tema = forms.MultipleChoiceField(label="Tema", required=False, choices=[])
    subtema = forms.MultipleChoiceField(label="Subtema", required=False, choices=[])
    difficulty = forms.ChoiceField(
        label="Dificuldade",
        required=False,
        choices=[("", "Todas")] + list(StudyQuestion.Difficulty.choices),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["area"].choices = [
            (val, val)
            for val in StudyTag.objects.order_by("area").values_list("area", flat=True).distinct()
            if val
        ]
        self.fields["tema"].choices = [
            (val, val)
            for val in StudyTag.objects.order_by("tema").values_list("tema", flat=True).distinct()
            if val
        ]
        self.fields["subtema"].choices = [
            (val, val)
            for val in StudyTag.objects.order_by("subtema").values_list("subtema", flat=True).distinct()
            if val
        ]
        self.fields["area"].widget.attrs["class"] = "form-select"
        self.fields["tema"].widget.attrs["class"] = "form-select"
        self.fields["subtema"].widget.attrs["class"] = "form-select"
        self.fields["difficulty"].widget.attrs["class"] = "form-select"
        self.fields["area"].widget.attrs["multiple"] = "multiple"
        self.fields["tema"].widget.attrs["multiple"] = "multiple"
        self.fields["subtema"].widget.attrs["multiple"] = "multiple"
        self.fields["area"].widget.attrs["size"] = "4"
        self.fields["tema"].widget.attrs["size"] = "4"
        self.fields["subtema"].widget.attrs["size"] = "4"
