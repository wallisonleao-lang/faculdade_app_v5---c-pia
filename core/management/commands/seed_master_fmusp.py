from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Course, ClassSession, Institution, InstitutionCourse, InstitutionClass
from core.services.institution_sync import mirror_master_classes
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Atribui dados antigos ao master e copia aulas para a instituição FMUSP."

    def handle(self, *args, **options):
        master_email = getattr(settings, "MASTER_EMAIL", "")
        if not master_email:
            self.stderr.write("MASTER_EMAIL não definido.")
            return

        User = get_user_model()
        try:
            master = User.objects.get(email=master_email)
        except User.DoesNotExist:
            self.stderr.write(f"Usuário master com email {master_email} não encontrado.")
            return

        institution = Institution.objects.filter(slug="fmusp").first()
        if not institution:
            institution = Institution.objects.filter(name="FMUSP").first()
        if not institution:
            institution = Institution.objects.create(name="FMUSP", slug="fmusp")
        elif institution.slug != "fmusp":
            institution.slug = "fmusp"
            institution.save(update_fields=["slug"])

        courses = Course.objects.filter(user__isnull=True)
        updated_courses = courses.count()
        courses.update(user=master)

        # Garantir vínculo com institution_course
        master_courses = Course.objects.filter(user=master)
        for course in master_courses:
            if course.institution_course_id:
                continue
            inst_course, _ = InstitutionCourse.objects.get_or_create(
                institution=institution,
                code=course.code or "",
                term=course.term or "",
                name=course.name,
            )
            course.institution_course = inst_course
            course.save(update_fields=["institution_course"])

        created_base, linked_classes, removed_base = mirror_master_classes(master)

        self.stdout.write(
            f"OK: {updated_courses} cursos atribuídos ao master, "
            f"{created_base} aulas-base criadas, {linked_classes} aulas vinculadas, "
            f"{removed_base} aulas-base removidas."
        )
