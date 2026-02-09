from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.feature_flags import feature_required
from hospital_game.services.activity_service import record_activity_completion
from study.forms import (
    StudyAnswerForm,
    StudyErrorLogForm,
    StudyQuestionFilterForm,
    StudyQuestionForm,
    StudyQuestionImportForm,
    StudyReviewAnswerForm,
    StudySessionStartForm,
)
from study.models import (
    StudyErrorLog,
    StudyQuestion,
    StudySession,
    StudySessionItem,
    StudyTag,
)
from study.services.recommendations import recommend_block
from study.services.sessions import create_session
from study.services.import_questions import import_questions_from_csv, import_questions_from_csv_text
from study.services.review import (
    apply_review_result,
    due_reviews_qs,
    last_error_log_for_question,
    schedule_from_error,
    select_similar_question,
)


def _choices_for_question(question: StudyQuestion):
    return [
        ("A", question.choice_a),
        ("B", question.choice_b),
        ("C", question.choice_c),
        ("D", question.choice_d),
        ("E", question.choice_e),
    ]


@login_required
@feature_required("study")
def study_home(request):
    due_count = due_reviews_qs(request.user).count()

    last_30 = timezone.now() - timedelta(days=30)
    items = StudySessionItem.objects.filter(session__user=request.user, session__started_at__gte=last_30)
    total = items.count()
    correct = items.filter(is_correct=True).count()
    accuracy = (correct / total) * 100 if total else 0
    avg_time = items.aggregate(avg=Avg("time_spent_seconds"))["avg"]

    recommended = recommend_block(request.user, planned_questions=20)
    recommended_tag = recommended["tag"]

    return render(
        request,
        "study/home.html",
        {
            "due_count": due_count,
            "accuracy": round(accuracy, 1),
            "avg_time": avg_time,
            "recommended_tag": recommended_tag,
            "recommended_questions": recommended["questions"],
        },
    )


@login_required
@feature_required("study")
def study_questions(request):
    form = StudyQuestionFilterForm(request.GET or None)
    qs = StudyQuestion.objects.select_related("tag", "source")

    if form.is_valid():
        areas = form.cleaned_data.get("area") or []
        temas = form.cleaned_data.get("tema") or []
        subtemas = form.cleaned_data.get("subtema") or []
        difficulty = form.cleaned_data.get("difficulty")
        if areas:
            qs = qs.filter(tag__area__in=areas)
        if temas:
            qs = qs.filter(tag__tema__in=temas)
        if subtemas:
            qs = qs.filter(tag__subtema__in=subtemas)
        if difficulty:
            qs = qs.filter(difficulty=difficulty)

    qs = qs.order_by("tag__area", "tag__tema", "tag__subtema", "id")
    return render(request, "study/questions.html", {"form": form, "questions": qs})


@login_required
@feature_required("study")
def study_question_create(request):
    if request.method == "POST":
        form = StudyQuestionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Questão cadastrada com sucesso.")
            return redirect("study_questions")
    else:
        form = StudyQuestionForm()

    return render(
        request,
        "study/question_form.html",
        {
            "form": form,
            "title": "Nova questão",
            "subtitle": "Cadastre enunciado e alternativas",
            "back_url": "/study/questions/",
        },
    )


@login_required
@feature_required("study")
def study_questions_import(request):
    if request.method == "POST":
        form = StudyQuestionImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data.get("file")
            pasted = (form.cleaned_data.get("pasted_csv") or "").strip()
            if f:
                result = import_questions_from_csv(f, user=request.user)
            elif pasted:
                result = import_questions_from_csv_text(pasted, user=request.user)
            else:
                messages.error(request, "Envie um arquivo CSV ou cole o conteúdo.")
                return render(request, "study/question_import.html", {"form": form})
            if result.errors:
                first = result.errors[:5]
                msg = "; ".join([f"Linha {e.line}: {e.message}" for e in first])
                if len(result.errors) > 5:
                    msg += f" (+{len(result.errors)-5} erros)"
                messages.error(request, f"Falha ao importar CSV. {msg}")
                return render(request, "study/question_import.html", {"form": form})
            messages.success(request, f"Importação concluída: {result.created} questões criadas.")
            return redirect("study_questions")
    else:
        form = StudyQuestionImportForm()

    return render(request, "study/question_import.html", {"form": form})


@login_required
@feature_required("study")
def study_session_start(request):
    if request.method == "POST":
        form = StudySessionStartForm(request.POST, user=request.user)
        if form.is_valid():
            planned_questions = form.cleaned_data["planned_questions"]
            target_minutes = form.cleaned_data["target_minutes"]
            area = form.cleaned_data.get("area") or []
            tema = form.cleaned_data.get("tema") or []
            subtema = form.cleaned_data.get("subtema") or []
            plan = form.cleaned_data.get("plan")

            recommended = recommend_block(
                request.user,
                planned_questions=planned_questions,
                area=area,
                tema=tema,
                subtema=subtema,
            )
            questions = recommended["questions"]

            if not questions:
                messages.warning(request, "Sem questões para esse filtro. Cadastre questões e tente novamente.")
                return redirect("study_questions")

            session = create_session(
                user=request.user,
                questions=questions,
                planned_questions=planned_questions,
                target_minutes=target_minutes,
                tag=recommended["tag"],
                plan=plan,
            )
            return redirect("study_session_player", session_id=session.id)
    else:
        form = StudySessionStartForm(user=request.user)

    return render(request, "study/session_start.html", {"form": form})


@login_required
@feature_required("study")
def study_session_player(request, session_id: int):
    session = get_object_or_404(StudySession, id=session_id, user=request.user)
    items = session.items.select_related("question", "question__tag").order_by("order")

    current_item = items.filter(is_correct__isnull=True).first()
    if not current_item:
        return redirect("study_session_results", session_id=session.id)

    show_result = False
    result_action = "continue"
    answered_item = current_item

    if request.method == "POST":
        item_id = request.POST.get("item_id")
        if item_id:
            answered_item = get_object_or_404(StudySessionItem, id=item_id, session=session)
        form = StudyAnswerForm(request.POST)
        if form.is_valid():
            if answered_item.is_correct is None:
                choice = form.cleaned_data["choice"]
                time_spent = form.cleaned_data.get("time_spent_seconds")
                flagged = form.cleaned_data.get("flagged_review") or False

                answered_item.user_answer = choice
                answered_item.is_correct = choice == answered_item.question.correct_choice
                answered_item.time_spent_seconds = time_spent
                answered_item.flagged_review = flagged
                answered_item.save(
                    update_fields=[
                        "user_answer",
                        "is_correct",
                        "time_spent_seconds",
                        "flagged_review",
                    ]
                )

                if answered_item.is_correct is False:
                    schedule_from_error(request.user, answered_item.question, session_item=answered_item)
            show_result = True
            result_action = (request.POST.get("action") or "continue").lower()
    else:
        form = StudyAnswerForm()

    progress_total = items.count()
    progress_current = items.filter(is_correct__isnull=True).count()
    progress_index = progress_total - progress_current + 1

    return render(
        request,
        "study/session_player.html",
        {
            "session": session,
            "item": answered_item if show_result else current_item,
            "question": (answered_item if show_result else current_item).question,
            "choices": _choices_for_question((answered_item if show_result else current_item).question),
            "form": form,
            "progress_index": progress_index,
            "progress_total": progress_total,
            "show_result": show_result,
            "result_action": result_action,
        },
    )


@login_required
@feature_required("study")
def study_session_results(request, session_id: int):
    session = get_object_or_404(StudySession, id=session_id, user=request.user)
    items = session.items.select_related("question", "question__tag").order_by("order")

    correct = items.filter(is_correct=True).count()
    total = items.count()
    accuracy = (correct / total) * 100 if total else 0

    if session.ended_at is None:
        session.ended_at = timezone.now()
        session.save(update_fields=["ended_at"])
        record_activity_completion(request.user, kind="STUDY_SESSION", object_id=session.id, completed_at=session.ended_at)

    if request.method == "POST":
        item_id = request.POST.get("item_id")
        item = get_object_or_404(StudySessionItem, id=item_id, session=session)
        if StudyErrorLog.objects.filter(user=request.user, session_item=item).exists():
            messages.info(request, "Erro já registrado para esta questão.")
            return redirect("study_session_results", session_id=session.id)
        form = StudyErrorLogForm(request.POST)
        if form.is_valid():
            error = form.save(commit=False)
            error.user = request.user
            error.question = item.question
            error.session_item = item
            error.save()
            schedule_from_error(request.user, item.question, session_item=item)
            messages.success(request, "Erro registrado e revisão agendada.")
            return redirect("study_session_results", session_id=session.id)
    incorrect_items = items.filter(is_correct=False)
    pending_count = items.filter(is_correct__isnull=True).count()
    logged_ids = set(
        StudyErrorLog.objects.filter(user=request.user, session_item__in=items)
        .values_list("session_item_id", flat=True)
    )
    for item in incorrect_items:
        item.has_error_log = item.id in logged_ids

    return render(
        request,
        "study/session_results.html",
        {
            "session": session,
            "items": items,
            "accuracy": round(accuracy, 1),
            "incorrect_items": incorrect_items,
            "error_reason_choices": StudyErrorLog.Reason.choices,
            "pending_count": pending_count,
        },
    )


@login_required
@feature_required("study")
def study_review_start(request):
    queue = due_reviews_qs(request.user)
    schedule = queue.first()

    if not schedule:
        messages.info(request, "Você está em dia com as revisões. Boa!")
        return render(request, "study/review_start.html", {"empty": True})

    question = schedule.question
    flashcard = last_error_log_for_question(request.user, question)
    similar = select_similar_question(question)
    choices = _choices_for_question(similar)

    if request.method == "POST":
        form = StudyReviewAnswerForm(request.POST)
        if form.is_valid():
            choice = form.cleaned_data["choice"]
            is_correct = choice == similar.correct_choice
            apply_review_result(request.user, question, is_correct)
            record_activity_completion(request.user, kind="STUDY_REVIEW", object_id=schedule.id)
            return redirect("study_review_start")
    else:
        form = StudyReviewAnswerForm()

    return render(
        request,
        "study/review_start.html",
        {
            "schedule": schedule,
            "question": question,
            "similar": similar,
            "flashcard": flashcard,
            "choices": choices,
            "form": form,
            "queue_count": queue.count(),
        },
    )


@login_required
@feature_required("study")
def study_dashboard(request):
    last_30 = timezone.now() - timedelta(days=30)
    items = StudySessionItem.objects.filter(session__user=request.user)

    accuracy = items.aggregate(
        total=Count("id"),
        correct=Count("id", filter=Q(is_correct=True)),
    )
    total = accuracy["total"] or 0
    correct = accuracy["correct"] or 0
    accuracy_pct = (correct / total) * 100 if total else 0

    avg_time = items.aggregate(avg=Avg("time_spent_seconds"))["avg"]

    by_subtema = (
        StudyErrorLog.objects
        .filter(user=request.user, created_at__gte=last_30)
        .values("question__tag__subtema", "question__tag__tema", "question__tag__area")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    by_area_rows = (
        items.values("question__tag__area")
        .annotate(
            total=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
        )
        .order_by("question__tag__area")
    )
    by_area = [
        {
            "label": row["question__tag__area"],
            "pct": round((row["correct"] / row["total"]) * 100, 1) if row["total"] else 0,
        }
        for row in by_area_rows
    ]

    by_tema_rows = (
        items.values("question__tag__tema")
        .annotate(
            total=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
        )
        .order_by("question__tag__tema")
    )
    by_tema = [
        {
            "label": row["question__tag__tema"],
            "pct": round((row["correct"] / row["total"]) * 100, 1) if row["total"] else 0,
        }
        for row in by_tema_rows
    ]

    due_count = due_reviews_qs(request.user).count()
    if due_count > 0:
        next_action = f"Você tem {due_count} revisão(ões) vencida(s)."
    else:
        next_action = "Inicie um bloco recomendado para manter o ritmo."

    return render(
        request,
        "study/dashboard.html",
        {
            "accuracy": round(accuracy_pct, 1),
            "avg_time": avg_time,
            "by_subtema": by_subtema,
            "by_area": by_area,
            "by_tema": by_tema,
            "next_action": next_action,
        },
    )


@login_required
@feature_required("study")
def study_tag_options(request):
    areas = [a for a in request.GET.getlist("area") if a]
    temas = [t for t in request.GET.getlist("tema") if t]

    qs = StudyTag.objects.all()
    if areas:
        qs = qs.filter(area__in=areas)
    if temas:
        qs = qs.filter(tema__in=temas)

    temas_values = [
        t
        for t in qs.order_by("tema").values_list("tema", flat=True).distinct()
        if t
    ]
    subtemas_values = [
        s
        for s in qs.order_by("subtema").values_list("subtema", flat=True).distinct()
        if s
    ]

    return JsonResponse({"temas": temas_values, "subtemas": subtemas_values})
