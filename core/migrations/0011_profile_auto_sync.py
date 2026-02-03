from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_seed_user_profiles"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="auto_sync_master_classes",
            field=models.BooleanField(default=False, verbose_name="Espelhamento automático de aulas"),
        ),
    ]
