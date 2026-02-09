from django.apps import AppConfig


class HospitalGameConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hospital_game"

    def ready(self) -> None:
        from . import signals  # noqa: F401
