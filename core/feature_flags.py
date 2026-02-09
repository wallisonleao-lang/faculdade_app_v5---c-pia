from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

from .models import FeatureFlag


DEFAULT_FEATURES = {
    "dashboard": True,
    "weekly_plan": True,
    "questions": False,
    "study": True,
    "courses": True,
    "absences": True,
    "quick_add": True,
}


def is_master_user(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    master_email = getattr(settings, "MASTER_EMAIL", "")
    if master_email and user.email and user.email.lower() == master_email.lower():
        return True
    return False


def get_feature_map():
    flags = {flag.key: flag.is_enabled for flag in FeatureFlag.objects.all()}
    merged = DEFAULT_FEATURES.copy()
    merged.update(flags)
    merged["questions"] = False
    return merged


def is_feature_enabled(user, key: str) -> bool:
    if is_master_user(user):
        return True
    return get_feature_map().get(key, True)


def feature_required(key: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not is_feature_enabled(request.user, key):
                messages.warning(request, "Esse recurso está temporariamente oculto.")
                features = get_feature_map()
                fallback_routes = {
                    "dashboard": "dashboard",
                    "courses": "courses_list",
                    "weekly_plan": "weekly_plan",
                    "questions": "study_home",
                    "absences": "absences",
                    "study": "study_home",
                }
                for fallback, route in fallback_routes.items():
                    if features.get(fallback, True) or is_master_user(request.user):
                        return redirect(route)
                return redirect("account_login")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
