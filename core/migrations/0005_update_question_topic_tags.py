from django.db import migrations


def replace_spaces_with_underscores(apps, schema_editor):
    Question = apps.get_model("core", "Question")
    for q in Question.objects.exclude(topic="").filter(topic__contains=" "):
        q.topic = q.topic.replace(" ", "_")
        q.save(update_fields=["topic"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_question_resolution"),
    ]

    operations = [
        migrations.RunPython(replace_spaces_with_underscores, migrations.RunPython.noop),
    ]
