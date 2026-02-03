from django.db import migrations


def seed_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("core", "UserProfile")
    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_seed_feature_flags"),
    ]

    operations = [
        migrations.RunPython(seed_profiles, migrations.RunPython.noop),
    ]
