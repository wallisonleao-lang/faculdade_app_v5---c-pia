from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_course_absences_count"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Institution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, unique=True, verbose_name="Instituição")),
                ("slug", models.SlugField(max_length=80, unique=True, verbose_name="Slug")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="FeatureFlag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=40, unique=True, verbose_name="Chave")),
                ("label", models.CharField(max_length=120, verbose_name="Nome")),
                ("is_enabled", models.BooleanField(default=True, verbose_name="Ativo")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["key"]},
        ),
        migrations.CreateModel(
            name="InstitutionCourse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(blank=True, max_length=30, verbose_name="Código")),
                ("name", models.CharField(max_length=200, verbose_name="Nome")),
                ("term", models.CharField(blank=True, max_length=20, verbose_name="Período")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("institution", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="courses", to="core.institution")),
            ],
            options={
                "ordering": ["name"],
                "unique_together": {("institution", "code", "term", "name")},
            },
        ),
        migrations.CreateModel(
            name="InstitutionClass",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="Título")),
                ("class_number", models.PositiveIntegerField(blank=True, null=True, verbose_name="Número da aula")),
                ("date", models.DateField(verbose_name="Data")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("institution_course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="classes", to="core.institutioncourse")),
            ],
            options={
                "ordering": ["date", "class_number", "title"],
                "unique_together": {("institution_course", "title", "class_number", "date")},
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_sync_at", models.DateTimeField(blank=True, null=True, verbose_name="Última sincronização")),
                ("institution", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="users", to="core.institution")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name="course",
            name="institution_course",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="user_courses", to="core.institutioncourse"),
        ),
        migrations.AddField(
            model_name="course",
            name="user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="courses", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="classsession",
            name="institution_class",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="user_classes", to="core.institutionclass"),
        ),
    ]
