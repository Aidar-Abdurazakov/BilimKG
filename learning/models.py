from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _


class School(models.Model):
    name = models.CharField(_("Название школы"), max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    ROLE = [("student", _("Ученик")), ("teacher", _("Учитель")), ("admin", _("Админ школы"))]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=12, choices=ROLE, default="student")
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.SET_NULL, related_name="members")
    class_name = models.CharField(_("Класс"), max_length=40, blank=True)
    must_change_password = models.BooleanField(default=False)

    @property
    def grade(self):
        digits = "".join(ch for ch in self.class_name if ch.isdigit())
        return int(digits) if digits else None

    def __str__(self):
        return f"{self.user} — {self.role}"


class Subject(models.Model):
    title = models.CharField(max_length=120)
    title_ky = models.CharField(max_length=120, blank=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#2f6bff")
    grade_from = models.PositiveSmallIntegerField(default=5)
    grade_to = models.PositiveSmallIntegerField(default=11)

    class Meta:
        ordering = ["title"]

    @property
    def name(self):
        return self.title_ky if get_language() == "ky" and self.title_ky else self.title

    def grades(self):
        return range(self.grade_from, self.grade_to + 1)

    def __str__(self):
        return self.title


class SchoolContent(models.Model):
    """school=None — общая библиотека BilimKG, видна всем школам."""
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.CASCADE, related_name="+")

    class Meta:
        abstract = True


class Topic(SchoolContent):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(_("Название"), max_length=200)
    grade = models.PositiveSmallIntegerField(_("Класс (5–11)"), default=5)
    order = models.PositiveSmallIntegerField(default=1)
    summary = models.TextField(blank=True)
    content = models.TextField(_("Текст темы"))
    estimated_minutes = models.PositiveSmallIntegerField(default=15)
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ["grade", "order", "id"]

    def __str__(self):
        return self.title


class Quiz(SchoolContent):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="quizzes")
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(_("Название"), max_length=200)
    grade = models.PositiveSmallIntegerField(_("Класс (5–11)"), default=5)
    class_name = models.CharField(_("Для класса (например 7А; пусто — всем)"), max_length=40, blank=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveSmallIntegerField(default=10)
    opens_at = models.DateTimeField(_("Открыть с"), null=True, blank=True)
    closes_at = models.DateTimeField(_("Закрыть (дедлайн)"), null=True, blank=True)
    published = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def is_open(self):
        now = timezone.now()
        return self.published and (not self.opens_at or now >= self.opens_at) and (not self.closes_at or now <= self.closes_at)

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField(_("Вопрос"))
    option_a = models.CharField("A", max_length=300)
    option_b = models.CharField("B", max_length=300)
    option_c = models.CharField("C", max_length=300, blank=True)
    option_d = models.CharField("D", max_length=300, blank=True)
    correct_option = models.CharField(_("Верный ответ"), max_length=1, choices=[(x, x) for x in "ABCD"])
    points = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def options(self):
        return [(k, v) for k, v in (("A", self.option_a), ("B", self.option_b), ("C", self.option_c), ("D", self.option_d)) if v]

    def __str__(self):
        return self.text[:60]


class QuizAttempt(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    answers = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    @property
    def percent(self):
        return round(self.score * 100 / self.max_score) if self.max_score else 0

    @property
    def mark(self):
        p = self.percent
        return 5 if p >= 90 else 4 if p >= 70 else 3 if p >= 50 else 2


class Assignment(SchoolContent):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(_("Название"), max_length=200)
    description = models.TextField(_("Условие"))
    grade = models.PositiveSmallIntegerField(_("Класс (5–11)"), default=5)
    class_name = models.CharField(_("Для класса (например 7А; пусто — всем)"), max_length=40, blank=True)
    deadline = models.DateTimeField(_("Срок сдачи"), null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    published = models.BooleanField(default=True)

    def is_open(self):
        return self.published and (not self.deadline or timezone.now() <= self.deadline)

    def __str__(self):
        return self.title


def upload_path(instance, filename):
    return f"submissions/student_{instance.student_id}/{filename}"


class Submission(models.Model):
    STATUS = [("pending", _("На проверке")), ("graded", _("Проверено"))]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions")
    image = models.ImageField(upload_to=upload_path)
    student_comment = models.TextField(blank=True)
    teacher_comment = models.TextField(blank=True)
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.assignment} — {self.student}"
