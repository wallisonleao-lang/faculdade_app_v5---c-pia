from django.utils import timezone

from .feature_flags import get_feature_map, is_master_user
from .models import InstitutionClass, UserProfile


def app_context(request):
    features = get_feature_map()
    is_master = is_master_user(request.user)
    sync_pending_count = 0
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            profile = None
        if profile and profile.institution:
            user_courses = request.user.courses.filter(
                institution_course__isnull=False,
                institution_course__institution=profile.institution,
            ).values_list("institution_course_id", flat=True)
            qs = InstitutionClass.objects.filter(institution_course_id__in=list(user_courses))
            if profile.last_sync_at:
                qs = qs.filter(updated_at__gt=profile.last_sync_at)
            sync_pending_count = qs.count()
    return {
        "features": features,
        "is_master": is_master,
        "sync_pending_count": sync_pending_count,
        "now": timezone.localtime(),
    }
