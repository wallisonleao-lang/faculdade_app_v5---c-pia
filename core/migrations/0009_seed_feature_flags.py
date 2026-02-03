from django.db import migrations


DEFAULT_FLAGS = [
    ("dashboard", "Dashboard", True),
    ("weekly_plan", "Planner semanal", True),
    ("questions", "Questões", True),
    ("courses", "Disciplinas", True),
    ("absences", "Faltas", True),
    ("quick_add", "Atalhos de criação", True),
]


def seed_flags(apps, schema_editor):
    FeatureFlag = apps.get_model("core", "FeatureFlag")
    for key, label, enabled in DEFAULT_FLAGS:
        FeatureFlag.objects.update_or_create(
            key=key, defaults={"label": label, "is_enabled": enabled}
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_institutions_features_user"),
    ]

    operations = [
        migrations.RunPython(seed_flags, migrations.RunPython.noop),
    ]
