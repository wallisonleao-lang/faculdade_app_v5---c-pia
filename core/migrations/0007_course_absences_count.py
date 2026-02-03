from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_question_classes"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="absences_count",
            field=models.PositiveIntegerField(default=0, verbose_name="Faltas"),
        ),
    ]
