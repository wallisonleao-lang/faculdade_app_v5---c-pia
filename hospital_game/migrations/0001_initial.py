from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(choices=[("TRIAGE", "Triagem"), ("WARD", "Enfermaria"), ("OR", "Centro cirúrgico"), ("LAB", "Laboratório")], max_length=20, unique=True)),
                ("label", models.CharField(max_length=100)),
                ("base_upgrade_seconds", models.PositiveIntegerField(default=60)),
                ("base_cost_energy", models.PositiveIntegerField(default=20)),
                ("base_cost_supplies", models.PositiveIntegerField(default=10)),
                ("max_level", models.PositiveIntegerField(default=10)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["key"],
            },
        ),
        migrations.CreateModel(
            name="HospitalProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("energy_total", models.PositiveIntegerField(default=0)),
                ("supplies_total", models.PositiveIntegerField(default=0)),
                ("reputation_total", models.PositiveIntegerField(default=0)),
                ("last_daily_claim_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="hospital_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["user_id"],
            },
        ),
        migrations.CreateModel(
            name="PatientCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=60, unique=True)),
                ("title", models.CharField(max_length=120)),
                ("rarity", models.CharField(choices=[("COMMON", "Comum"), ("RARE", "Rara"), ("EPIC", "Épica")], max_length=10)),
                ("flavor_text", models.TextField(blank=True)),
            ],
            options={
                "ordering": ["rarity", "title"],
            },
        ),
        migrations.CreateModel(
            name="TaskCompletionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("task_id", models.PositiveIntegerField(unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="task_completion_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DailyLedger",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("energy_earned", models.PositiveIntegerField(default=0)),
                ("supplies_earned", models.PositiveIntegerField(default=0)),
                ("tasks_completed_count", models.PositiveIntegerField(default=0)),
                ("daily_claimed", models.BooleanField(default=False)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hospital_ledgers", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-date", "user_id"],
                "unique_together": {("user", "date")},
            },
        ),
        migrations.CreateModel(
            name="UserDepartment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("level", models.PositiveIntegerField(default=0)),
                ("upgrade_ends_at", models.DateTimeField(blank=True, null=True)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_departments", to="hospital_game.department")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hospital_departments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["department__key", "user_id"],
                "unique_together": {("user", "department")},
            },
        ),
        migrations.CreateModel(
            name="UserPatientCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("count", models.PositiveIntegerField(default=0)),
                ("card", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_cards", to="hospital_game.patientcard")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="patient_cards", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["card__rarity", "card__title"],
                "unique_together": {("user", "card")},
            },
        ),
    ]
