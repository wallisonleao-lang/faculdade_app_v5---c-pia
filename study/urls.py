from django.urls import path

from . import views

urlpatterns = [
    path("", views.study_dashboard, name="study_home"),
    path("home/", views.study_home, name="study_today"),
    path("api/tag-options/", views.study_tag_options, name="study_tag_options"),
    path("questions/", views.study_questions, name="study_questions"),
    path("questions/new/", views.study_question_create, name="study_question_new"),
    path("questions/import/", views.study_questions_import, name="study_questions_import"),
    path("sessions/start/", views.study_session_start, name="study_session_start"),
    path("sessions/<int:session_id>/", views.study_session_player, name="study_session_player"),
    path("sessions/<int:session_id>/results/", views.study_session_results, name="study_session_results"),
    path("review/start/", views.study_review_start, name="study_review_start"),
    path("dashboard/", views.study_dashboard, name="study_dashboard"),
]
