from django.contrib.auth import get_user_model
from django.test import TestCase
from study.models import StudyErrorLog, StudyQuestion, StudyReviewSchedule, StudyTag
from study.services.recommendations import recommend_block
from study.services.review import apply_review_result, schedule_from_error
from study.services.sessions import create_session


User = get_user_model()


def _make_question(tag: StudyTag, idx: int):
    return StudyQuestion.objects.create(
        tag=tag,
        enunciado=f"Questão {idx}",
        choice_a="A",
        choice_b="B",
        choice_c="C",
        choice_d="D",
        choice_e="E",
        correct_choice="A",
        difficulty="MEDIUM",
    )


class StudyReviewScheduleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", email="u1@example.com", password="test")
        self.tag = StudyTag.objects.create(area="Clínica", tema="Cardio", subtema="IC")
        self.question = _make_question(self.tag, 1)

    def test_review_progression(self):
        schedule = schedule_from_error(self.user, self.question)
        self.assertEqual(schedule.stage, StudyReviewSchedule.Stage.STAGE_1)
        self.assertTrue(schedule.active)

        schedule, completed = apply_review_result(self.user, self.question, is_correct=True)
        self.assertEqual(schedule.stage, StudyReviewSchedule.Stage.STAGE_2)
        self.assertFalse(completed)

        schedule, completed = apply_review_result(self.user, self.question, is_correct=True)
        self.assertEqual(schedule.stage, StudyReviewSchedule.Stage.STAGE_3)
        self.assertFalse(completed)

        schedule, completed = apply_review_result(self.user, self.question, is_correct=True)
        self.assertFalse(schedule.active)
        self.assertTrue(completed)

        schedule = schedule_from_error(self.user, self.question)
        schedule, completed = apply_review_result(self.user, self.question, is_correct=False)
        self.assertEqual(schedule.stage, StudyReviewSchedule.Stage.STAGE_1)
        self.assertTrue(schedule.active)
        self.assertFalse(completed)


class StudyRecommendationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u2", email="u2@example.com", password="test")
        self.tag1 = StudyTag.objects.create(area="Clínica", tema="Cardio", subtema="IC")
        self.tag2 = StudyTag.objects.create(area="Cirurgia", tema="Abdome", subtema="Hérnias")
        self.q1 = _make_question(self.tag1, 1)
        self.q2 = _make_question(self.tag1, 2)
        self.q3 = _make_question(self.tag2, 3)

        StudyErrorLog.objects.create(
            user=self.user,
            question=self.q1,
            error_reason="CONTEUDO",
            rule_of_thumb="Regra",
        )
        StudyErrorLog.objects.create(
            user=self.user,
            question=self.q2,
            error_reason="CONTEUDO",
            rule_of_thumb="Regra",
        )

    def test_recommendation_prefers_top_error_tag(self):
        result = recommend_block(self.user, planned_questions=2, area=["Clínica"], tema=["Cardio"], subtema=["IC"])
        self.assertIsNotNone(result["tag"])
        self.assertEqual(result["tag"].id, self.tag1.id)
        self.assertTrue(all(q.tag_id == self.tag1.id for q in result["questions"]))


class StudySessionCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u3", email="u3@example.com", password="test")
        self.tag = StudyTag.objects.create(area="GO", tema="Pré-natal", subtema="Diabetes")
        self.questions = [_make_question(self.tag, idx) for idx in range(1, 6)]

    def test_session_creates_items(self):
        session = create_session(
            user=self.user,
            questions=self.questions,
            planned_questions=5,
            target_minutes=60,
            tag=self.tag,
            plan=None,
        )
        self.assertEqual(session.items.count(), 5)
