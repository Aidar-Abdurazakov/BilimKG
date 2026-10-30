from django.contrib.auth import views as auth
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.password_reset, name="password_reset"),
    path("password-reset/done/", auth.PasswordResetDoneView.as_view(template_name="password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth.PasswordResetConfirmView.as_view(template_name="password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth.PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"), name="password_reset_complete"),
    path("password-change/", views.ChangePassword.as_view(), name="password_change"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("subjects/", views.subjects, name="subjects"),
    path("subjects/<int:pk>/", views.subject_detail, name="subject_detail"),
    path("topics/<int:pk>/", views.topic_detail, name="topic_detail"),
    path("quizzes/", views.quizzes, name="quizzes"),
    path("quizzes/<int:pk>/", views.take_quiz, name="take_quiz"),
    path("assignments/", views.assignments, name="assignments"),
    path("assignments/<int:pk>/submit/", views.submit_assignment, name="submit_assignment"),
    path("my-submissions/", views.my_submissions, name="my_submissions"),
    path("teacher/", views.teacher, name="teacher"),
    path("teacher/submissions/", views.teacher_submissions, name="teacher_submissions"),
    path("teacher/submissions/<int:pk>/", views.grade_submission, name="grade_submission"),
    path("results/", views.results, name="results"),
    path("content/", views.content_list, name="content_list"),
    path("content/<str:kind>/new/", views.content_edit, name="content_new"),
    path("content/<str:kind>/<int:pk>/", views.content_edit, name="content_edit"),
    path("content/<str:kind>/<int:pk>/delete/", views.content_delete, name="content_delete"),
    path("platform/", views.platform_home, name="platform_home"),
    path("school/", views.school_home, name="school"),
    path("school/users/add/", views.user_add, name="user_add"),
    path("school/users/import/", views.user_import, name="user_import"),
    path("school/users/<int:pk>/reset/", views.user_reset, name="user_reset"),
    path("school/users/<int:pk>/toggle/", views.user_toggle, name="user_toggle"),
]
