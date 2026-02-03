from django.db import transaction

from core.models import ClassSession, Institution, InstitutionClass, InstitutionCourse


def mirror_master_classes(master_user, institution_slug="fmusp"):
    institution = Institution.objects.filter(slug=institution_slug).first()
    if not institution:
        return 0, 0, 0

    master_courses = master_user.courses.select_related("institution_course")
    created_base = 0
    linked_classes = 0
    removed_base = 0

    with transaction.atomic():
        for course in master_courses:
            inst_course = course.institution_course
            if not inst_course:
                inst_course, _ = InstitutionCourse.objects.get_or_create(
                    institution=institution,
                    code=course.code or "",
                    term=course.term or "",
                    name=course.name,
                )
                course.institution_course = inst_course
                course.save(update_fields=["institution_course"])

            master_classes = ClassSession.objects.filter(course=course)
            master_keys = {(c.title, c.class_number, c.date) for c in master_classes}

            for cls in master_classes:
                inst_class, created = InstitutionClass.objects.get_or_create(
                    institution_course=inst_course,
                    title=cls.title,
                    class_number=cls.class_number,
                    date=cls.date,
                )
                if created:
                    created_base += 1
                if cls.institution_class_id != inst_class.id:
                    cls.institution_class = inst_class
                    cls.save(update_fields=["institution_class"])
                    linked_classes += 1

            extra_ids = []
            for inst_cls in InstitutionClass.objects.filter(institution_course=inst_course):
                key = (inst_cls.title, inst_cls.class_number, inst_cls.date)
                if key not in master_keys:
                    extra_ids.append(inst_cls.id)
            if extra_ids:
                removed_base += InstitutionClass.objects.filter(id__in=extra_ids).count()
                InstitutionClass.objects.filter(id__in=extra_ids).delete()

    return created_base, linked_classes, removed_base
