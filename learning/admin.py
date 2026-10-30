from django.contrib import admin

from .models import *


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "school", "class_name")
    list_filter = ("role", "school")
    search_fields = ("user__username", "user__last_name")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("title", "title_ky", "grade_from", "grade_to")
    prepopulated_fields = {"slug": ("title",)}


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 2


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "grade", "school", "published")
    list_filter = ("school", "subject", "grade")
    inlines = [QuestionInline]


for m in (Topic, Assignment, Submission, QuizAttempt):
    admin.site.register(m)
