from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Course, Task
from hospital_game.models import DailyLedger, Department, HospitalProfile, UserDepartment
from hospital_game.services.claim_service import claim_daily
from hospital_game.services.ledger_service import record_task_completion
from hospital_game.services.upgrade_service import finish_upgrade, start_upgrade


User = get_user_model()


class HospitalGameTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="pass1234")
        self.client = Client()
        self.client.force_login(self.user)

    def _create_course_task(self):
        course = Course.objects.create(user=self.user, name="Teste", term="2026-1")
        task = Task.objects.create(course=course, title="Tarefa", status="DONE", done_at=timezone.now())
        return task

    def test_status_creates_hospital_profile(self):
        self.assertFalse(HospitalProfile.objects.filter(user=self.user).exists())
        response = self.client.get(reverse("hospital_status"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(HospitalProfile.objects.filter(user=self.user).exists())

    def test_record_task_completion_creates_ledger(self):
        task = self._create_course_task()
        result = record_task_completion(task, completed_at=task.done_at)
        self.assertTrue(result.created)
        ledger = DailyLedger.objects.get(user=self.user, date=timezone.localdate(task.done_at))
        self.assertEqual(ledger.energy_earned, 5)
        self.assertEqual(ledger.supplies_earned, 1)
        self.assertEqual(ledger.tasks_completed_count, 1)

    def test_claim_daily_requires_task(self):
        result = claim_daily(self.user)
        self.assertEqual(result.status, "invalid")

    def test_claim_daily_idempotent(self):
        task = self._create_course_task()
        record_task_completion(task, completed_at=task.done_at)
        result1 = claim_daily(self.user)
        self.assertEqual(result1.status, "claimed")
        result2 = claim_daily(self.user)
        self.assertEqual(result2.status, "already_claimed")

    def test_start_upgrade_deducts_resources(self):
        department = Department.objects.create(
            key="TRIAGE",
            label="Triagem",
            base_upgrade_seconds=60,
            base_cost_energy=20,
            base_cost_supplies=10,
            max_level=10,
        )
        profile = HospitalProfile.objects.create(user=self.user, energy_total=50, supplies_total=50)

        result = start_upgrade(self.user, department.key)
        self.assertEqual(result.status, "started")
        profile.refresh_from_db()
        user_department = UserDepartment.objects.get(user=self.user, department=department)
        self.assertEqual(profile.energy_total, 30)
        self.assertEqual(profile.supplies_total, 40)
        self.assertIsNotNone(user_department.upgrade_ends_at)

    def test_finish_upgrade_requires_time(self):
        department = Department.objects.create(
            key="LAB",
            label="Laboratório",
            base_upgrade_seconds=60,
            base_cost_energy=10,
            base_cost_supplies=5,
            max_level=10,
        )
        user_department = UserDepartment.objects.create(
            user=self.user,
            department=department,
            level=0,
            upgrade_ends_at=timezone.now() + timedelta(minutes=10),
        )

        result = finish_upgrade(self.user, department.key)
        self.assertEqual(result.status, "conflict")

        user_department.upgrade_ends_at = timezone.now() - timedelta(seconds=5)
        user_department.save(update_fields=["upgrade_ends_at"])

        result = finish_upgrade(self.user, department.key)
        self.assertEqual(result.status, "finished")
        user_department.refresh_from_db()
        self.assertEqual(user_department.level, 1)
        self.assertIsNone(user_department.upgrade_ends_at)
