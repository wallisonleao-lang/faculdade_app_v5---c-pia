from django.urls import path

from hospital_game import views

urlpatterns = [
    path("", views.hospital_dashboard, name="hospital_dashboard"),
    path("collection/", views.collection_view, name="hospital_collection"),
    path("api/status/", views.api_status, name="hospital_status"),
    path("api/claim/", views.api_claim, name="hospital_claim"),
    path("api/department/<str:key>/start_upgrade/", views.api_start_upgrade, name="hospital_start_upgrade"),
    path("api/department/<str:key>/finish_upgrade/", views.api_finish_upgrade, name="hospital_finish_upgrade"),
]
