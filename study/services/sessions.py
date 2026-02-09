from django.db import transaction

from study.models import StudyPlan, StudyQuestion, StudySession, StudySessionItem, StudyTag


def create_session(*, user, questions: list[StudyQuestion], planned_questions: int, target_minutes: int | None, tag: StudyTag | None, plan: StudyPlan | None):
    with transaction.atomic():
        session = StudySession.objects.create(
            user=user,
            plan=plan,
            mode=StudySession.Mode.BLOCK,
            planned_questions=planned_questions,
            target_minutes=target_minutes,
            recommended_tag=tag,
        )
        for idx, question in enumerate(questions, start=1):
            StudySessionItem.objects.create(
                session=session,
                question=question,
                order=idx,
            )
    return session
