from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Avg, Count, Q
import math
import random

from django.contrib.auth.decorators import login_required
from core.feature_flags import feature_required, is_master_user, DEFAULT_FEATURES
from core.forms import (
    CourseForm,
    TaskForm,
    ClassSessionForm,
    ExamForm,
    QuestionForm,
    QuestionAttemptForm,
    QuestionImportForm,
    InstitutionForm,
    ProfileInstitutionForm,
)
from core.models import (
    Task,
    ClassSession,
    Course,
    Exam,
    Question,
    QuestionAttempt,
    QuestionOption,
    InstitutionClass,
    FeatureFlag,
    UserProfile,
)
from django.forms import inlineformset_factory
from core.services.priority import compute_dashboard_items
from django.contrib import messages
from django.views.decorators.http import require_POST
from core.services.import_classes import import_classes_from_csv
from core.services.import_questions import import_questions_from_csv, import_questions_from_csv_text


def _tag_filter_q(field_name, tokens):
    q = Q()
    for t in tokens:
        q |= Q(**{f"{field_name}__iexact": t})
        q |= Q(**{f"{field_name}__istartswith": f"{t} "})
        q |= Q(**{f"{field_name}__iendswith": f" {t}"})
        q |= Q(**{f"{field_name}__icontains": f" {t} "})
    return q


def _class_label(cls):
    prefix = f"Aula {cls.class_number} - " if cls.class_number else ""
    return f"{prefix}{cls.title}"


@login_required
@feature_required("dashboard")
def dashboard_view(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    if not profile.has_seen_wizard:
        return redirect("wizard")
    items = compute_dashboard_items(user=request.user)
    return render(request, "core/dashboard.html", {"items": items})

@login_required
@feature_required("absences")
def absences_view(request):
    courses = Course.objects.filter(user=request.user).order_by("name").prefetch_related("classes")
    entries = []
    for course in courses:
        total_classes = course.classes.values("date").distinct().count()
        limit = math.floor(total_classes * 0.2)
        absences = course.absences_count
        over_limit = limit > 0 and absences > limit
        usage_pct = 0
        if limit > 0:
            usage_pct = min(100, int(round((absences / limit) * 100)))
        entries.append(
            {
                "course": course,
                "total_classes": total_classes,
                "limit": limit,
                "absences": absences,
                "over_limit": over_limit,
                "usage_pct": usage_pct,
            }
        )
    return render(request, "core/absences.html", {"entries": entries})

@login_required
@feature_required("absences")
@require_POST
def absences_update_view(request, course_id):
    course = get_object_or_404(Course, id=course_id, user=request.user)
    action = (request.POST.get("action") or "").lower()
    if action == "inc":
        course.absences_count += 1
    elif action == "dec":
        course.absences_count = max(0, course.absences_count - 1)
    elif action == "set":
        try:
            value = int(request.POST.get("value", "0"))
        except (TypeError, ValueError):
            value = course.absences_count
        course.absences_count = max(0, value)
    course.save(update_fields=["absences_count"])
    next_url = request.POST.get("next") or "/faltas/"
    return redirect(next_url)

@login_required
@feature_required("weekly_plan")
def weekly_plan_view(request):
    today = timezone.localdate()
    week_dates = [today + timedelta(days=i) for i in range(7)]

    plan = {d: [] for d in week_dates}
    load = {d: 0 for d in week_dates}

    dashboard_items = compute_dashboard_items(today=today, limit=None, user=request.user)
    task_scores = {item.source_id: item.score for item in dashboard_items if item.kind == "TAREFA"}
    review_scores = {
        (item.kind, item.source_id): item.score
        for item in dashboard_items
        if item.kind in {"REVISAO_P1", "REVISAO_P2"}
    }

    exams = (
        Exam.objects.select_related("course")
        .filter(date__gte=today, course__user=request.user)
        .order_by("date")
    )

    def add_item(target_date, item):
        plan[target_date].append(item)
        load[target_date] += item["points"]

    def _priority_days_for_item(item, fallback_date):
        priority_date = fallback_date
        if item["kind"] == "TASK":
            priority_date = item.get("due_date") or item.get("good_by") or fallback_date
        if priority_date is None:
            return 9999
        return (priority_date - today).days

    def _priority_score_for_item(item, exam):
        if item["kind"] == "TASK":
            return task_scores.get(item.get("task_id"))
        if exam.type == "P1":
            return review_scores.get(("REVISAO_P1", exam.course.id))
        if exam.type == "P2":
            return review_scores.get(("REVISAO_P2", exam.course.id))
        return None

    entries = []

    for exam in exams:
        available_dates = [d for d in week_dates if d <= exam.date]
        if not available_dates:
            continue

        classes_qs = exam.course.classes.filter(watched=True)
        tasks_qs = exam.course.tasks.filter(status__in=["TODO", "DOING"])

        items = []

        if exam.type == "P1":
            classes_qs = classes_qs.filter(reviewed_p1=False)
            for cls in classes_qs:
                title = f"Revisar P1: Aula {cls.class_number}" if cls.class_number else f"Revisar P1: {cls.title}"
                items.append(
                    {
                        "kind": "CLASS",
                        "title": title,
                        "course": exam.course,
                        "points": 1,
                        "class_id": cls.id,
                        "watched": cls.watched,
                    }
                )
        elif exam.type == "P2":
            classes_qs = classes_qs.filter(reviewed_p2=False)
            for cls in classes_qs:
                title = f"Revisar P2: Aula {cls.class_number}" if cls.class_number else f"Revisar P2: {cls.title}"
                items.append(
                    {
                        "kind": "CLASS",
                        "title": title,
                        "course": exam.course,
                        "points": 1,
                        "class_id": cls.id,
                        "watched": cls.watched,
                    }
                )
        else:
            for cls in classes_qs:
                title = f"Revisar: Aula {cls.class_number}" if cls.class_number else f"Revisar: {cls.title}"
                items.append(
                    {
                        "kind": "CLASS",
                        "title": title,
                        "course": exam.course,
                        "points": 1,
                        "class_id": cls.id,
                        "watched": cls.watched,
                    }
                )

        for task in tasks_qs:
            items.append(
                {
                    "kind": "TASK",
                    "title": task.title,
                    "course": exam.course,
                    "points": 2,
                    "task_id": task.id,
                    "due_date": task.due_date,
                    "good_by": task.good_by,
                }
            )

        for item in items:
            entries.append(
                {
                    "item": item,
                    "available_dates": available_dates,
                    "priority_score": _priority_score_for_item(item, exam),
                    "priority_days": _priority_days_for_item(item, exam.date),
                    "kind_weight": 0 if item["kind"] == "TASK" else 1,
                }
            )

    entries.sort(
        key=lambda e: (
            -(e["priority_score"] or -1),
            e["priority_days"],
            e["kind_weight"],
        )
    )

    for entry in entries:
        target_date = min(entry["available_dates"], key=lambda d: (load[d], d))
        add_item(target_date, entry["item"])

    def load_label(points):
        if points <= 3:
            return ("Baixa", "bg-success-subtle text-success")
        if points <= 7:
            return ("Média", "bg-warning-subtle text-warning")
        return ("Alta", "bg-danger-subtle text-danger")

    days = []
    for d in week_dates:
        label, badge_class = load_label(load[d])
        days.append(
            {
                "date": d,
                "items": plan[d],
                "points": load[d],
                "load_label": label,
                "badge_class": badge_class,
            }
        )

    return render(request, "core/weekly_plan.html", {"days": days, "today": today})


@login_required
def profile_view(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    profile_form = ProfileInstitutionForm(
        request.POST or None,
        instance=profile,
        prefix="profile",
    )
    institution_form = None
    if is_master_user(request.user):
        institution_form = InstitutionForm(
            request.POST or None,
            prefix="institution",
        )

    if request.method == "POST":
        if request.POST.get("action") == "save_profile" and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Instituição atualizada.")
            return redirect("profile")
        if (
            request.POST.get("action") == "create_institution"
            and institution_form
            and institution_form.is_valid()
        ):
            institution_form.save()
            messages.success(request, "Instituição criada.")
            return redirect("profile")

    return render(
        request,
        "core/profile.html",
        {"profile_form": profile_form, "institution_form": institution_form},
    )


@login_required
def guide_view(request):
    return render(request, "core/guide.html")


@login_required
def wizard_view(request):
    return render(request, "core/wizard.html")


@login_required
@require_POST
def wizard_complete_view(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    profile.has_seen_wizard = True
    profile.save(update_fields=["has_seen_wizard"])
    return redirect("dashboard")

@login_required
def master_panel_view(request):
    if not is_master_user(request.user):
        messages.error(request, "Acesso restrito ao usuário master.")
        return redirect("dashboard")

    if request.method == "POST":
        for key, default_enabled in DEFAULT_FEATURES.items():
            enabled = request.POST.get(f"feature_{key}") == "on"
            FeatureFlag.objects.update_or_create(
                key=key,
                defaults={"label": key.replace("_", " ").title(), "is_enabled": enabled},
            )
        messages.success(request, "Configurações atualizadas.")
        return redirect("master_panel")

    flags = {flag.key: flag for flag in FeatureFlag.objects.all()}
    features = []
    for key, default_enabled in DEFAULT_FEATURES.items():
        flag = flags.get(key)
        features.append(
            {
                "key": key,
                "label": flag.label if flag else key.replace("_", " ").title(),
                "is_enabled": flag.is_enabled if flag else default_enabled,
            }
        )

    return render(request, "core/master_panel.html", {"features": features})


@login_required
@feature_required("courses")
@require_POST
def sync_institution_classes_view(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None
    if not profile or not profile.institution:
        messages.error(request, "Selecione uma instituição para sincronizar.")
        return redirect(request.POST.get("next") or "dashboard")

    user_courses = Course.objects.filter(
        user=request.user,
        institution_course__isnull=False,
        institution_course__institution=profile.institution,
    ).select_related("institution_course")
    if not user_courses.exists():
        messages.info(request, "Nenhuma disciplina vinculada à instituição para sincronizar.")
        return redirect(request.POST.get("next") or "dashboard")

    created_count = 0
    with transaction.atomic():
        for course in user_courses:
            base_classes = InstitutionClass.objects.filter(
                institution_course=course.institution_course
            ).order_by("date", "class_number", "title")
            for base in base_classes:
                if ClassSession.objects.filter(course=course, institution_class=base).exists():
                    continue
                ClassSession.objects.create(
                    course=course,
                    institution_class=base,
                    title=base.title,
                    class_number=base.class_number,
                    date=base.date,
                )
                created_count += 1
        profile.last_sync_at = timezone.now()
        profile.save(update_fields=["last_sync_at"])

    messages.success(request, f"Sincronização concluída: {created_count} aula(s) importada(s).")
    return redirect(request.POST.get("next") or "dashboard")

@login_required
@feature_required("questions")
def questions_board_view(request):
    course_id = request.GET.get("course")
    topic_values = request.GET.getlist("topic")
    if not topic_values:
        topic_single = (request.GET.get("topic") or "").strip()
        topic_values = [topic_single] if topic_single else []
    class_values = request.GET.getlist("class")
    class_ids = []
    for val in class_values:
        try:
            class_ids.append(int(val))
        except (TypeError, ValueError):
            continue
    show_list = (request.GET.get("list") or "").lower() in {"1", "true", "yes"}
    courses = Course.objects.filter(user=request.user).order_by("name")
    classes_qs = ClassSession.objects.filter(course__user=request.user).order_by("date", "class_number", "title")
    if course_id:
        classes_qs = classes_qs.filter(course_id=course_id)
    valid_class_ids = set(classes_qs.values_list("id", flat=True))
    selected_class_ids = [cid for cid in class_ids if cid in valid_class_ids]
    classes = [{"id": c.id, "label": _class_label(c)} for c in classes_qs]
    topic_set = set()
    for t in Question.objects.filter(course__user=request.user).exclude(topic="").values_list("topic", flat=True):
        for token in t.split():
            topic_set.add(token)
    topics = sorted(topic_set)

    questions_qs = Question.objects.select_related("course").filter(course__user=request.user)
    attempts_qs = QuestionAttempt.objects.select_related("question__course").filter(question__course__user=request.user)

    if course_id:
        questions_qs = questions_qs.filter(course_id=course_id)
        attempts_qs = attempts_qs.filter(question__course_id=course_id)
    if topic_values:
        topic_tokens = [t for t in topic_values if t]
        questions_qs = questions_qs.filter(_tag_filter_q("topic", topic_tokens))
        attempts_qs = attempts_qs.filter(_tag_filter_q("question__topic", topic_tokens))
    if selected_class_ids:
        questions_qs = questions_qs.filter(classes__id__in=selected_class_ids).distinct()
        attempts_qs = attempts_qs.filter(question__classes__id__in=selected_class_ids).distinct()

    attempts = attempts_qs
    total_attempts = attempts.count()
    correct_attempts = attempts.filter(is_correct=True).count()
    accuracy = (correct_attempts / total_attempts) * 100 if total_attempts else 0
    avg_time = attempts.aggregate(avg=Avg("time_seconds"))["avg"]

    by_class_qs = (
        classes_qs.annotate(
            total_attempts=Count("questions__attempts"),
            correct_attempts=Count("questions__attempts", filter=Q(questions__attempts__is_correct=True)),
        )
        .order_by("date", "class_number", "title")
    )
    by_class = [
        {
            "label": _class_label(cls),
            "total_attempts": cls.total_attempts,
            "correct_attempts": cls.correct_attempts,
        }
        for cls in by_class_qs
    ]

    most_missed = (
        questions_qs.annotate(
            incorrect_attempts=Count("attempts", filter=Q(attempts__is_correct=False)),
            total_attempts=Count("attempts"),
        )
        .filter(total_attempts__gt=0)
        .order_by("-incorrect_attempts", "-total_attempts")[:5]
    )

    questions = (
        questions_qs.annotate(
            attempts_total=Count("attempts"),
            attempts_correct=Count("attempts", filter=Q(attempts__is_correct=True)),
            attempts_incorrect=Count("attempts", filter=Q(attempts__is_correct=False)),
        )
        .order_by("course__name", "topic", "title")
    )

    return render(
        request,
        "core/questions_board.html",
        {
            "questions": questions,
            "total_attempts": total_attempts,
            "correct_attempts": correct_attempts,
            "accuracy": round(accuracy, 1),
            "avg_time": avg_time,
            "by_class": by_class,
            "most_missed": most_missed,
            "courses": courses,
            "classes": classes,
            "topics": topics,
            "selected_course": int(course_id) if course_id else None,
            "selected_topics": topic_values,
            "topic_query": "&".join([f"topic={t}" for t in topic_values]),
            "selected_classes": selected_class_ids,
            "class_query": "&".join([f"class={cid}" for cid in selected_class_ids]),
            "show_list": show_list,
        },
    )


@login_required
@feature_required("questions")
def question_create_view(request):
    OptionFormSet = inlineformset_factory(
        Question,
        QuestionOption,
        fields=("text", "is_correct"),
        extra=4,
        min_num=2,
        validate_min=True,
        can_delete=False,
    )

    topic_set = set()
    for t in Question.objects.filter(course__user=request.user).exclude(topic="").values_list("topic", flat=True):
        for token in t.split():
            topic_set.add(token)
    existing_topics = sorted(topic_set)

    if request.method == "POST":
        form = QuestionForm(request.POST, user=request.user)
        formset = OptionFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            correct_count = 0
            for opt_form in formset:
                if opt_form.cleaned_data.get("is_correct"):
                    correct_count += 1

            if correct_count != 1:
                messages.error(request, "Marque exatamente 1 alternativa como correta.")
            else:
                question = form.save()
                formset.instance = question
                formset.save()
                return redirect("questions_board")
    else:
        form = QuestionForm(user=request.user)
        formset = OptionFormSet()

    return render(
        request,
        "core/question_form.html",
        {
            "form": form,
            "formset": formset,
            "topics": existing_topics,
            "title": "Nova questão",
            "subtitle": "Cadastre enunciado e alternativas",
            "back_url": "/questions/",
        },
    )


@login_required
@feature_required("questions")
def question_edit_view(request, id):
    question = get_object_or_404(Question, id=id, course__user=request.user)
    OptionFormSet = inlineformset_factory(
        Question,
        QuestionOption,
        fields=("text", "is_correct"),
        extra=0,
        min_num=2,
        validate_min=True,
        can_delete=False,
    )

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question, user=request.user)
        formset = OptionFormSet(request.POST, instance=question)
        if form.is_valid() and formset.is_valid():
            correct_count = 0
            for opt_form in formset:
                if opt_form.cleaned_data.get("is_correct"):
                    correct_count += 1

            if correct_count != 1:
                messages.error(request, "Marque exatamente 1 alternativa como correta.")
            else:
                form.save()
                formset.save()
                return redirect("questions_board")
    else:
        form = QuestionForm(instance=question, user=request.user)
        formset = OptionFormSet(instance=question)

    return render(
        request,
        "core/question_form.html",
        {
            "form": form,
            "formset": formset,
            "topics": sorted(
                {
                    token
                    for t in Question.objects.filter(course__user=request.user).exclude(topic="").values_list("topic", flat=True)
                    for token in t.split()
                }
            ),
            "title": "Editar questão",
            "subtitle": "Atualize enunciado e alternativas",
            "back_url": "/questions/",
        },
    )


@login_required
@feature_required("questions")
def question_attempt_create_view(request, question_id=None):
    if request.method == "POST":
        form = QuestionAttemptForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect("questions_board")
    else:
        initial = None
        if question_id and Question.objects.filter(id=question_id, course__user=request.user).exists():
            initial = {"question": question_id}
        form = QuestionAttemptForm(initial=initial, user=request.user)

    return render(
        request,
        "core/form.html",
        {"form": form, "title": "Registrar tentativa", "subtitle": "Acerto/erro e tempo", "back_url": "/questions/"},
    )


@login_required
@feature_required("questions")
@require_POST
def import_questions_csv(request):
    form = QuestionImportForm(request.POST, request.FILES, user=request.user)
    if not form.is_valid():
        messages.error(request, "Verifique os campos da importação.")
        return render(request, "core/question_import.html", {"form": form})

    course = form.cleaned_data["course"]
    if course.user_id != request.user.id:
        messages.error(request, "Você não tem acesso a essa disciplina.")
        return redirect("questions_board")
    classes = form.cleaned_data.get("classes")
    f = form.cleaned_data.get("file")
    pasted = (form.cleaned_data.get("pasted_csv") or "").strip()

    if f:
        result = import_questions_from_csv(course, f, classes=classes)
    elif pasted:
        result = import_questions_from_csv_text(course, pasted, classes=classes)
    else:
        messages.error(request, "Envie um arquivo CSV ou cole o conteúdo.")
        return render(request, "core/question_import.html", {"form": form})
    if result.errors:
        first = result.errors[:5]
        msg = "; ".join([f"Linha {e.line}: {e.message}" for e in first])
        if len(result.errors) > 5:
            msg += f" (+{len(result.errors)-5} erros)"
        messages.error(request, f"Falha ao importar CSV. {msg}")
        return render(request, "core/question_import.html", {"form": form})

    messages.success(request, f"Importação concluída: {result.created} questões criadas.")
    return redirect("questions_board")


@login_required
@feature_required("questions")
def questions_import_view(request):
    course_id = request.GET.get("course")
    initial = {}
    if course_id:
        try:
            course_id_int = int(course_id)
            if Course.objects.filter(id=course_id_int, user=request.user).exists():
                initial["course"] = course_id_int
        except (TypeError, ValueError):
            initial = {}
    form = QuestionImportForm(initial=initial, user=request.user)
    return render(request, "core/question_import.html", {"form": form})


@login_required
@feature_required("questions")
def question_quiz_view(request):
    filter_status = request.GET.get("status") or "all"
    question_id_param = request.GET.get("q")
    next_flag = request.GET.get("next")
    topic_values = request.GET.getlist("topic") or request.POST.getlist("topic")
    if not topic_values:
        topic_single = (request.GET.get("topic") or request.POST.get("topic") or "").strip()
        topic_values = [topic_single] if topic_single else []
    topic_query = "&".join([f"topic={t}" for t in topic_values])
    class_values = request.GET.getlist("class") or request.POST.getlist("class")
    class_ids = []
    for val in class_values:
        try:
            class_ids.append(int(val))
        except (TypeError, ValueError):
            continue
    class_query = "&".join([f"class={cid}" for cid in class_ids])

    if request.method == "POST":
        question_id = request.POST.get("question_id")
        option_id = request.POST.get("option_id")
        status = request.POST.get("status") or "all"
        question = get_object_or_404(Question, id=question_id, course__user=request.user)
        selected = QuestionOption.objects.filter(id=option_id, question=question).first()
        correct_option = QuestionOption.objects.filter(question=question, is_correct=True).first()
        is_correct = bool(selected and selected.is_correct)

        QuestionAttempt.objects.create(
            question=question,
            selected_option=selected,
            is_correct=is_correct,
        )

        request.session["quiz_feedback"] = {
            "is_correct": is_correct,
            "selected_text": selected.text if selected else None,
            "correct_text": correct_option.text if correct_option else None,
        }

        target = f"/questions/quiz/?q={question.id}"
        if status and status != "all":
            target += f"&status={status}"
        if topic_query:
            target += f"&{topic_query}"
        if class_query:
            target += f"&{class_query}"
        return redirect(target)

    base_qs = (
        Question.objects.prefetch_related("options")
        .filter(options__isnull=False, course__user=request.user)
        .distinct()
    )
    if topic_values:
        topic_tokens = [t for t in topic_values if t]
        base_qs = base_qs.filter(_tag_filter_q("topic", topic_tokens))
    if class_ids:
        base_qs = base_qs.filter(classes__id__in=class_ids).distinct()

    if filter_status == "correct":
        base_qs = base_qs.filter(attempts__is_correct=True).distinct()
    elif filter_status == "incorrect":
        base_qs = base_qs.annotate(
            correct_attempts=Count("attempts", filter=Q(attempts__is_correct=True)),
            total_attempts=Count("attempts"),
        ).filter(total_attempts__gt=0, correct_attempts=0)
    elif filter_status == "unattempted":
        base_qs = base_qs.filter(attempts__isnull=True)
    elif filter_status == "attempted":
        base_qs = base_qs.filter(attempts__isnull=False).distinct()

    total_in_filter = base_qs.count()

    topic_set = set()
    for t in Question.objects.filter(course__user=request.user).exclude(topic="").values_list("topic", flat=True):
        for token in t.split():
            topic_set.add(token)
    topics = sorted(topic_set)
    classes = [
        {"id": c.id, "label": _class_label(c)}
        for c in ClassSession.objects.filter(course__user=request.user).order_by("date", "class_number", "title")
    ]

    if total_in_filter == 0:
        messages.info(request, "Sem questões para esse filtro. Ajuste o filtro ou cadastre questões.")
        return render(
            request,
            "core/question_quiz.html",
            {
                "question": None,
                "options": [],
                "filter_status": filter_status,
                "selected_topics": topic_values,
                "topic_query": topic_query,
                "topic_label": ", ".join(topic_values),
                "selected_classes": class_ids,
                "class_query": class_query,
                "feedback": None,
                "progress_current": 0,
                "progress_total": 0,
                "topics": topics,
                "classes": classes,
                "empty_state": True,
            },
        )

    topic_key = "_".join([t for t in topic_values if t]) or "all"
    session_list_key = f"quiz_list_{filter_status}_{topic_key}"
    session_index_key = f"quiz_index_{filter_status}_{topic_key}"

    quiz_list = request.session.get(session_list_key)
    quiz_index = request.session.get(session_index_key, 0)

    if not quiz_list or len(quiz_list) != total_in_filter:
        quiz_list = list(base_qs.values_list("id", flat=True))
        random.shuffle(quiz_list)
        quiz_index = 0
        request.session[session_list_key] = quiz_list
        request.session[session_index_key] = quiz_index

    if next_flag:
        quiz_index = min(quiz_index + 1, max(total_in_filter - 1, 0))
        request.session[session_index_key] = quiz_index
        next_id = quiz_list[quiz_index]
        target = f"/questions/quiz/?q={next_id}&status={filter_status}"
        if topic_query:
            target += f"&{topic_query}"
        if class_query:
            target += f"&{class_query}"
        return redirect(target)

    if question_id_param:
        question = (
            Question.objects.prefetch_related("options")
            .filter(options__isnull=False, id=question_id_param, course__user=request.user)
            .first()
        )
        if not question:
            messages.info(request, "Questão não encontrada.")
            return redirect("question_quiz")
        options = question.options.all()
        feedback = request.session.pop("quiz_feedback", None)
        current_pos = quiz_list.index(question.id) + 1 if question.id in quiz_list else 1
        return render(
            request,
            "core/question_quiz.html",
            {
                "question": question,
                "options": options,
                "filter_status": filter_status,
                "selected_topics": topic_values,
                "topic_query": topic_query,
                "topic_label": ", ".join(topic_values),
                "selected_classes": class_ids,
                "class_query": class_query,
                "feedback": feedback,
                "progress_current": current_pos,
                "progress_total": total_in_filter,
                "topics": topics,
                "classes": classes,
            },
        )

    question_id = quiz_list[quiz_index]
    question = (
        Question.objects.prefetch_related("options")
        .filter(options__isnull=False, id=question_id, course__user=request.user)
        .first()
    )

    if not question:
        messages.info(request, "Sem questões para esse filtro. Ajuste o filtro ou cadastre questões.")
        return redirect("question_quiz")

    options = question.options.all()
    feedback = request.session.pop("quiz_feedback", None)
    return render(
        request,
        "core/question_quiz.html",
        {
            "question": question,
            "options": options,
            "filter_status": filter_status,
            "selected_topics": topic_values,
            "topic_query": topic_query,
            "topic_label": ", ".join(topic_values),
            "selected_classes": class_ids,
            "class_query": class_query,
            "feedback": feedback,
            "progress_current": quiz_index + 1,
            "progress_total": total_in_filter,
            "topics": topics,
            "classes": classes,
        },
    )


@login_required
@feature_required("courses")
def courses_list_view(request):
    courses = Course.objects.filter(user=request.user).order_by("name")
    return render(request, "core/courses_list.html", {"courses": courses})


@login_required
@feature_required("courses")
def course_detail_view(request, id):
    course = get_object_or_404(Course, id=id, user=request.user)

    exams = course.exams.all().order_by("date")
    classes = course.classes.all().order_by("date", "class_number", "title")
    tasks = course.tasks.all().order_by("status", "due_date", "good_by", "title")

    total_classes = classes.count()
    watched_count = classes.filter(watched=True).count()
    reviewed_p1_count = classes.filter(reviewed_p1=True).count()
    reviewed_p2_count = classes.filter(reviewed_p2=True).count()

    progress = {
        "total_classes": total_classes,
        "watched_count": watched_count,
        "reviewed_p1_count": reviewed_p1_count,
        "reviewed_p2_count": reviewed_p2_count,
        "watched_pct": int((watched_count / total_classes) * 100) if total_classes else 0,
        "p1_pct": int((reviewed_p1_count / total_classes) * 100) if total_classes else 0,
        "p2_pct": int((reviewed_p2_count / total_classes) * 100) if total_classes else 0,
    }

    return render(
        request,
        "core/course_detail.html",
        {"course": course, "exams": exams, "classes": classes, "tasks": tasks, "progress": progress},
    )


@login_required
@feature_required("courses")
def course_create_view(request):
    if request.method == "POST":
        form = CourseForm(request.POST, user=request.user)
        if form.is_valid():
            course = form.save(commit=False)
            course.user = request.user
            course.save()
            return redirect("course_detail", id=course.id)
    else:
        form = CourseForm(user=request.user)

    return render(
        request,
        "core/form.html",
        {"form": form, "title": "Nova disciplina", "subtitle": "Cadastre uma UC/Disciplina", "back_url": "/courses/"},
    )


@login_required
@feature_required("courses")
def task_create_view(request, course_id=None):
    if request.method == "POST":
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save()
            return redirect("course_detail", id=task.course.id)
    else:
        initial = {"course": course_id} if course_id else None
        form = TaskForm(initial=initial, user=request.user)

    back_url = f"/courses/{course_id}/" if course_id else "/dashboard/"
    return render(
        request,
        "core/form.html",
        {"form": form, "title": "Nova tarefa", "subtitle": "Crie uma tarefa com prazos", "back_url": back_url},
    )


@login_required
@feature_required("courses")
def class_create_view(request, course_id=None):
    if request.method == "POST":
        form = ClassSessionForm(request.POST, user=request.user)
        if form.is_valid():
            cls = form.save()
            return redirect("course_detail", id=cls.course.id)
    else:
        initial = {"course": course_id} if course_id else None
        form = ClassSessionForm(initial=initial, user=request.user)

    back_url = f"/courses/{course_id}/" if course_id else "/dashboard/"
    return render(
        request,
        "core/form.html",
        {"form": form, "title": "Nova aula", "subtitle": "Registre uma aula do semestre", "back_url": back_url},
    )


@login_required
@feature_required("courses")
def exam_create_view(request, course_id=None):
    if request.method == "POST":
        form = ExamForm(request.POST, user=request.user)
        if form.is_valid():
            exam = form.save()
            return redirect("course_detail", id=exam.course.id)
    else:
        initial = {"course": course_id} if course_id else None
        form = ExamForm(initial=initial, user=request.user)

    back_url = f"/courses/{course_id}/" if course_id else "/dashboard/"
    return render(
        request,
        "core/form.html",
        {"form": form, "title": "Nova prova", "subtitle": "Cadastre P1/P2 e datas", "back_url": back_url},
    )


@login_required
@feature_required("courses")
def task_mark_done_view(request, id):
    task = get_object_or_404(Task, id=id, course__user=request.user)
    task.status = "DONE"
    task.done_at = timezone.now()
    task.save()
    return redirect(request.GET.get("next", "dashboard"))


@login_required
@feature_required("courses")
def class_mark_watched_view(request, id):
    cls = get_object_or_404(ClassSession, id=id, course__user=request.user)
    cls.watched = True
    cls.save()
    return redirect(request.GET.get("next", "dashboard"))

@login_required
@feature_required("courses")
def class_mark_review_p1_view(request, id):
    cls = get_object_or_404(ClassSession, id=id, course__user=request.user)
    cls.reviewed_p1 = True
    cls.save()
    return redirect(request.GET.get("next", "dashboard"))

@login_required
@feature_required("courses")
def class_mark_review_p2_view(request, id):
    cls = get_object_or_404(ClassSession, id=id, course__user=request.user)
    cls.reviewed_p2 = True
    cls.save()
    return redirect(request.GET.get("next", "dashboard"))

@login_required
@feature_required("courses")
def course_mark_review_p1_done_view(request, course_id):
    ClassSession.objects.filter(course_id=course_id, reviewed_p1=False, course__user=request.user).update(reviewed_p1=True)
    return redirect(request.GET.get("next", "/"))

@login_required
@feature_required("courses")
def course_mark_review_p2_done_view(request, course_id):
    ClassSession.objects.filter(course_id=course_id, reviewed_p2=False, course__user=request.user).update(reviewed_p2=True)
    return redirect(request.GET.get("next", "/"))

@login_required
@feature_required("courses")
@require_POST
def import_classes_csv(request, course_id: int):
    course = get_object_or_404(Course, id=course_id, user=request.user)

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")

    f = request.FILES.get("csv_file")
    if not f:
        messages.error(request, "Envie um arquivo CSV para importar.")
        if next_url:
            return redirect(next_url)
        return redirect("course_detail", id=course.id)

    result = import_classes_from_csv(course, f)

    if result.errors:
        first = result.errors[:5]
        msg = "; ".join([f"Linha {e.line}: {e.message}" for e in first])
        if len(result.errors) > 5:
            msg += f" (+{len(result.errors)-5} erros)"
        messages.error(request, f"Falha ao importar CSV. {msg}")
        if next_url:
            return redirect(next_url)
        return redirect("course_detail", id=course.id)

    messages.success(
        request,
        f"Importação concluída: {result.created} criadas, {result.updated} atualizadas, {result.skipped} sem mudanças."
    )
    if next_url:
        return redirect(next_url)
    return redirect("course_detail", id=course.id)
