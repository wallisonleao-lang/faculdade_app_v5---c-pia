from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_update_question_topic_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="classes",
            field=models.ManyToManyField(
                blank=True,
                related_name="questions",
                to="core.classsession",
                verbose_name="Aulas",
            ),
        ),
    ]
