from django.urls import path
from core import views
from .views import (
    dashboard_view,
    absences_view,
    absences_update_view,
    courses_list_view,
    course_detail_view,
    course_create_view,
    task_create_view,
    class_create_view,
    exam_create_view,
    task_mark_done_view,
    class_mark_watched_view,
    class_mark_review_p1_view,
    class_mark_review_p2_view,
    course_mark_review_p1_done_view,
    course_mark_review_p2_done_view,
    weekly_plan_view,
    profile_view,
    guide_view,
    wizard_view,
    wizard_complete_view,
    master_panel_view,
    sync_institution_classes_view,
)

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("faltas/", absences_view, name="absences"),
    path("faltas/<int:course_id>/", absences_update_view, name="absences_update"),
    path("courses/", courses_list_view, name="courses_list"),
    path("courses/new/", course_create_view, name="course_new"),
    path("courses/<int:id>/", course_detail_view, name="course_detail"),

    path("tasks/new/", task_create_view, name="task_new"),
    path("courses/<int:course_id>/tasks/new/", task_create_view, name="task_new_for_course"),
    path("tasks/<int:id>/done/", task_mark_done_view, name="task_done"),

    path("classes/new/", class_create_view, name="class_new"),
    path("courses/<int:course_id>/classes/new/", class_create_view, name="class_new_for_course"),
    path("classes/<int:id>/watched/", class_mark_watched_view, name="class_watched"),

    path("exams/new/", exam_create_view, name="exam_new"),
    path("courses/<int:course_id>/exams/new/", exam_create_view, name="exam_new_for_course"),

    path("classes/<int:id>/review-p1/", class_mark_review_p1_view, name="class_review_p1"),
    path("classes/<int:id>/review-p2/", class_mark_review_p2_view, name="class_review_p2"),

    path("courses/<int:course_id>/review-p1/done/", course_mark_review_p1_done_view, name="course_review_p1_done"),
    path("courses/<int:course_id>/review-p2/done/", course_mark_review_p2_done_view, name="course_review_p2_done"),

    path("courses/<int:course_id>/import-classes-csv/", views.import_classes_csv, name="import_classes_csv"),
    path("planner/", weekly_plan_view, name="weekly_plan"),
    path("profile/", profile_view, name="profile"),
    path("guia/", guide_view, name="guide"),
    path("wizard/", wizard_view, name="wizard"),
    path("wizard/complete/", wizard_complete_view, name="wizard_complete"),
    path("sync/classes/", sync_institution_classes_view, name="sync_institution_classes"),
    path("master/", master_panel_view, name="master_panel"),

]
