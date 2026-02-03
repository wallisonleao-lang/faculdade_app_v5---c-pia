from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_profile_auto_sync"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="has_seen_wizard",
            field=models.BooleanField(default=False, verbose_name="Viu o guia inicial"),
        ),
    ]
