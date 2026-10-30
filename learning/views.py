import re
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordChangeView
from django.db import transaction
from django.db.models import Avg, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _

from .forms import AssignmentForm, ImportForm, QuestionFormSet, QuizForm, SchoolSetupForm, TopicForm, UserAddForm
from .models import *
from .utils import create_account, make_password, norm_class

User = get_user_model()
STAFF = ("teacher", "admin", "owner")


def role(user):
    if user.is_superuser:
        return "owner"
    p = getattr(user, "profile", None)
    return p.role if p else "student"


def roles(*allowed):
    def deco(view):
        @wraps(view)
        def inner(request, *a, **k):
            if role(request.user) not in allowed:
                return HttpResponseForbidden(_("Нет доступа"))
            return view(request, *a, **k)
        return login_required(inner)
    return deco


def school_of(user):
    return None if user.is_superuser else user.profile.school


def vis(qs, user, classed=False):
    """Что видит пользователь: общая библиотека + материалы своей школы (ученик — только опубликованное для своего класса)."""
    r = role(user)
    if r == "owner":
        return qs
    s = user.profile.school
    qs = qs.filter(Q(school__isnull=True) | Q(school=s)) if s else qs.filter(school__isnull=True)
    if r == "student":
        qs = qs.filter(published=True)
        if classed:
            qs = qs.filter(Q(class_name="") | Q(class_name=user.profile.class_name))
    return qs


def school_students(user):
    # Технический суперпользователь не должен отображаться в списке учеников,
    # даже если у его Profile по умолчанию стоит роль student.
    qs = User.objects.filter(
        profile__role="student", is_active=True, is_superuser=False
    ).select_related("profile")
    return qs if user.is_superuser else qs.filter(profile__school=school_of(user))


# ---------- вход ----------
def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html", {"subjects": Subject.objects.count()})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    error = ""
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("username", "").strip(), password=request.POST.get("password", ""))
        if user:
            login(request, user)
            nxt = request.GET.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else "dashboard")
        error = _("Неверный логин или пароль.")
    return render(request, "login.html", {"error": error})


@login_required
def logout_view(request):
    if request.method != "POST":
        return HttpResponseForbidden()
    logout(request)
    return redirect("home")


def password_reset(request):
    form = PasswordResetForm(request.POST or None)
    sent = False
    if request.method == "POST" and form.is_valid():
        form.save(request=request, use_https=request.is_secure(), email_template_name="registration/password_reset_email.html", subject_template_name="registration/password_reset_subject.txt")
        sent = True
    return render(request, "password_reset.html", {"form": form, "sent": sent})


class ChangePassword(PasswordChangeView):
    template_name = "password_change.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        resp = super().form_valid(form)
        p = self.request.user.profile
        p.must_change_password = False
        p.save(update_fields=["must_change_password"])
        messages.success(self.request, _("Пароль изменён."))
        return resp


# ---------- кабинет ----------
@login_required
def dashboard(request):
    u, r = request.user, role(request.user)
    ctx = {"role": r}
    if r == "student":
        done = set(QuizAttempt.objects.filter(student=u).values_list("quiz_id", flat=True))
        sent = set(Submission.objects.filter(student=u).values_list("assignment_id", flat=True))
        ctx["todo_quizzes"] = [q for q in vis(Quiz.objects.select_related("subject"), u, True) if q.is_open() and q.id not in done][:6]
        ctx["todo_assignments"] = [a for a in vis(Assignment.objects.select_related("subject"), u, True) if a.is_open() and a.id not in sent][:6]
        ctx["attempts"] = QuizAttempt.objects.filter(student=u).select_related("quiz")[:5]
        ctx["grade"] = u.profile.grade
    else:
        scope = Submission.objects.all() if r == "owner" else Submission.objects.filter(student__profile__school=school_of(u))
        ctx["pending"] = scope.filter(status="pending").count()
        ctx["students"] = school_students(u).count()
        if r != "owner":
            ctx["teachers"] = User.objects.filter(profile__school=school_of(u), profile__role="teacher").count()
        else:
            ctx["schools_count"] = School.objects.count()
            ctx["admins_count"] = User.objects.filter(profile__role="admin", is_active=True).count()
    return render(request, "dashboard.html", ctx)


# ---------- ученик: предметы, темы, тесты ----------
def _grade_param(request):
    g = request.GET.get("grade", "")
    if g.isdigit() and 5 <= int(g) <= 11:
        return int(g)
    if g == "all":
        return None
    return request.user.profile.grade if role(request.user) == "student" else None


@login_required
def subjects(request):
    g = _grade_param(request)
    qs = Subject.objects.filter(grade_from__lte=g, grade_to__gte=g) if g else Subject.objects.all()
    return render(request, "subjects.html", {"subjects": qs, "grade": g, "grades": range(5, 12)})


@login_required
def subject_detail(request, pk):
    s = get_object_or_404(Subject, pk=pk)
    g = _grade_param(request)
    f = {"grade": g} if g else {}
    return render(request, "subject.html", {
        "subject": s, "grade": g, "grades": s.grades(),
        "topics": vis(s.topics.all(), request.user).filter(**f),
        "quizzes": vis(s.quizzes.all(), request.user, True).filter(**f),
        "assignments": vis(s.assignments.all(), request.user, True).filter(**f),
        "can_edit": role(request.user) in STAFF,
    })


@login_required
def topic_detail(request, pk):
    t = get_object_or_404(vis(Topic.objects.select_related("subject"), request.user), pk=pk)
    return render(request, "topic.html", {"topic": t, "quizzes": vis(Quiz.objects.filter(subject=t.subject, grade=t.grade), request.user, True)[:3]})


@login_required
def quizzes(request):
    g = _grade_param(request)
    qs = vis(Quiz.objects.select_related("subject"), request.user, True)
    if g:
        qs = qs.filter(grade=g)
    best = {}
    for a in QuizAttempt.objects.filter(student=request.user):
        best[a.quiz_id] = max(best.get(a.quiz_id, 0), a.percent)
    items = [(q, best.get(q.id)) for q in qs]
    return render(request, "quizzes.html", {"items": items, "grade": g, "grades": range(5, 12)})


@login_required
def take_quiz(request, pk):
    quiz = get_object_or_404(vis(Quiz.objects.select_related("subject"), request.user, True), pk=pk)
    if not quiz.is_open():
        messages.error(request, _("Тест сейчас недоступен."))
        return redirect("quizzes")
    qs = list(quiz.questions.all())
    if request.method == "POST":
        answers, score, review = {}, 0, []
        for q in qs:
            a = request.POST.get(f"q{q.id}", "")
            answers[str(q.id)] = a
            if a == q.correct_option:
                score += q.points
            review.append((q, a, dict(q.options()).get(a, ""), dict(q.options()).get(q.correct_option, "")))
        attempt = QuizAttempt.objects.create(student=request.user, quiz=quiz, score=score, max_score=sum(q.points for q in qs), answers=answers)
        return render(request, "result.html", {"attempt": attempt, "review": review})
    return render(request, "take_quiz.html", {"quiz": quiz, "questions": qs})


@login_required
def assignments(request):
    g = _grade_param(request)
    qs = vis(Assignment.objects.select_related("subject"), request.user, True)
    if g:
        qs = qs.filter(grade=g)
    sent = set(Submission.objects.filter(student=request.user).values_list("assignment_id", flat=True))
    return render(request, "assignments.html", {"items": [(a, a.id in sent) for a in qs], "grade": g, "grades": range(5, 12)})


@roles("student")
def submit_assignment(request, pk):
    a = get_object_or_404(vis(Assignment.objects, request.user, True), pk=pk)
    if not a.is_open():
        messages.error(request, _("Срок сдачи прошёл."))
        return redirect("assignments")
    if request.method == "POST":
        files = request.FILES.getlist("image")
        if not files:
            messages.error(request, _("Выберите фото."))
        elif len(files) > 6:
            messages.error(request, _("Не больше 6 фото за раз."))
        elif any(f.size > 8 * 1024 * 1024 for f in files):
            messages.error(request, _("Каждое фото — не больше 8 МБ."))
        elif any(f.content_type not in ("image/jpeg", "image/png", "image/webp") for f in files):
            messages.error(request, _("Разрешены JPG, PNG, WEBP."))
        else:
            for f in files:
                Submission.objects.create(assignment=a, student=request.user, image=f, student_comment=request.POST.get("student_comment", "")[:1000])
            messages.success(request, _("Работа отправлена. Учитель скоро проверит."))
            return redirect("my_submissions")
    return render(request, "submit.html", {"assignment": a})


@login_required
def my_submissions(request):
    return render(request, "my_submissions.html", {"submissions": Submission.objects.filter(student=request.user).select_related("assignment")})


# ---------- учитель ----------
def _subs(user):
    qs = Submission.objects.select_related("student__profile", "assignment")
    return qs if user.is_superuser else qs.filter(student__profile__school=school_of(user))


@roles(*STAFF)
def teacher(request):
    return render(request, "teacher.html", {"pending": _subs(request.user).filter(status="pending")[:30]})


@roles(*STAFF)
def teacher_submissions(request):
    qs, cls = _subs(request.user), norm_class(request.GET.get("class", ""))
    if cls:
        qs = qs.filter(student__profile__class_name=cls)
    if request.GET.get("status") in ("pending", "graded"):
        qs = qs.filter(status=request.GET["status"])
    return render(request, "teacher_submissions.html", {"submissions": qs[:200], "cls": cls, "status": request.GET.get("status", "")})


@roles(*STAFF)
def grade_submission(request, pk):
    s = get_object_or_404(_subs(request.user), pk=pk)
    if request.method == "POST":
        g = request.POST.get("grade", "")
        if g in ("2", "3", "4", "5"):
            s.grade, s.teacher_comment, s.status, s.reviewed_at = int(g), request.POST.get("teacher_comment", "")[:2000], "graded", timezone.now()
            s.save()
            messages.success(request, _("Оценка сохранена."))
            nxt = _subs(request.user).filter(status="pending").exclude(pk=s.pk).first()
            return redirect("grade_submission", nxt.pk) if nxt and request.POST.get("next") else redirect("teacher_submissions")
        messages.error(request, _("Выберите оценку."))
    return render(request, "grade.html", {"s": s})


@roles(*STAFF)
def results(request):
    cls = norm_class(request.GET.get("class", ""))
    students = school_students(request.user)
    classes = sorted(set(students.values_list("profile__class_name", flat=True)))
    if cls:
        students = students.filter(profile__class_name=cls)
    rows = []
    for st in students.order_by("profile__class_name", "last_name", "first_name"):
        att = list(QuizAttempt.objects.filter(student=st))
        marks = [a.mark for a in att]
        graded = list(Submission.objects.filter(student=st, grade__isnull=False).values_list("grade", flat=True))
        rows.append({"user": st, "tests": len({a.quiz_id for a in att}), "avg_test": round(sum(marks) / len(marks), 1) if marks else None, "works": len(graded), "avg_work": round(sum(graded) / len(graded), 1) if graded else None})
    return render(request, "results.html", {"rows": rows, "classes": classes, "cls": cls})


# ---------- создание материалов (учитель и админ школы) ----------
KINDS = {"topic": (Topic, TopicForm, "Тема"), "quiz": (Quiz, QuizForm, "Тест"), "assignment": (Assignment, AssignmentForm, "Контрольная")}


@roles(*STAFF)
def content_list(request):
    s = school_of(request.user)
    f = {} if request.user.is_superuser else {"school": s}
    return render(request, "content_list.html", {
        "topics": Topic.objects.filter(**f).select_related("subject").order_by("-id")[:100],
        "quizzes": Quiz.objects.filter(**f).select_related("subject").order_by("-id")[:100],
        "assignments": Assignment.objects.filter(**f).select_related("subject").order_by("-id")[:100],
    })


@roles(*STAFF)
def content_edit(request, kind, pk=None):
    if kind not in KINDS:
        return HttpResponseForbidden()
    model, form_cls, label = KINDS[kind]
    school = school_of(request.user)
    obj = None
    if pk:
        obj = get_object_or_404(model, pk=pk)
        if not request.user.is_superuser and obj.school_id != (school.id if school else None):
            return HttpResponseForbidden(_("Нет доступа"))
    elif not school and not request.user.is_superuser:
        return HttpResponseForbidden(_("Вас не назначили в школу"))
    initial = {k: request.GET[k] for k in ("subject", "grade") if k in request.GET}
    form = form_cls(request.POST or None, instance=obj, initial=initial)
    formset = QuestionFormSet(request.POST or None, instance=obj) if kind == "quiz" else None
    if request.method == "POST" and form.is_valid() and (formset is None or formset.is_valid()):
        o = form.save(commit=False)
        if not pk:
            o.school = school
            if hasattr(o, "created_by"):
                o.created_by = request.user
        o.save()
        if formset is not None:
            formset.instance = o
            formset.save()
        messages.success(request, _("Сохранено."))
        return redirect("content_list")
    return render(request, "content_form.html", {"form": form, "formset": formset, "kind": kind, "label": label, "obj": obj})


@roles(*STAFF)
def content_delete(request, kind, pk):
    if kind not in KINDS or request.method != "POST":
        return HttpResponseForbidden()
    obj = get_object_or_404(KINDS[kind][0], pk=pk)
    s = school_of(request.user)
    if not request.user.is_superuser and obj.school_id != (s.id if s else None):
        return HttpResponseForbidden()
    obj.delete()
    messages.success(request, _("Удалено."))
    return redirect("content_list")


# ---------- суперадминистратор платформы ----------
@roles("owner")
def platform_home(request):
    form = SchoolSetupForm(request.POST or None)
    created_account = None
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            school = School.objects.create(name=form.cleaned_data["school_name"])
            admin_user, temporary_password = create_account(
                school,
                form.cleaned_data["admin_full_name"],
                "admin",
            )
        created_account = {"school": school, "user": admin_user, "password": temporary_password}
        form = SchoolSetupForm()
        messages.success(request, _("Школа и аккаунт администратора созданы."))
    schools = School.objects.all().order_by("name")
    school_rows = []
    for school in schools:
        members = User.objects.filter(profile__school=school, is_active=True)
        school_rows.append({
            "school": school,
            "students": members.filter(profile__role="student").count(),
            "teachers": members.filter(profile__role="teacher").count(),
            "admins": members.filter(profile__role="admin").count(),
        })
    return render(request, "platform.html", {
        "form": form,
        "school_rows": school_rows,
        "created_account": created_account,
    })


# ---------- админ школы: пользователи ----------
def _need_school(request):
    return request.user.profile.school is not None


@roles("admin")
def school_home(request):
    s = request.user.profile.school
    q, rl = request.GET.get("q", "").strip(), request.GET.get("role", "")
    users = User.objects.filter(profile__school=s).select_related("profile").order_by("profile__role", "profile__class_name", "last_name")
    if q:
        users = users.filter(Q(last_name__icontains=q) | Q(first_name__icontains=q) | Q(username__icontains=q) | Q(profile__class_name__icontains=norm_class(q)))
    if rl in ("student", "teacher", "admin"):
        users = users.filter(profile__role=rl)
    return render(request, "school.html", {"school": s, "users": users[:300], "q": q, "rl": rl})


@roles("admin")
def user_add(request):
    form = UserAddForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        user, pw = create_account(request.user.profile.school, d["full_name"], d["role"], d["class_name"])
        return render(request, "user_created.html", {"accounts": [(user, pw)]})
    return render(request, "user_add.html", {"form": form})


@roles("admin")
def user_import(request):
    form = ImportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        accounts = []
        for line in form.cleaned_data["lines"].splitlines():
            parts = [p.strip() for p in re.split(r"[;,\t]", line) if p.strip()]
            if not parts or (form.cleaned_data["role"] == "student" and len(parts) < 2):
                continue
            accounts.append(create_account(request.user.profile.school, parts[0], form.cleaned_data["role"], parts[1] if len(parts) > 1 else ""))
        if not accounts:
            messages.error(request, _("Не нашли ни одной строки в нужном формате."))
        else:
            return render(request, "user_created.html", {"accounts": accounts})
    return render(request, "user_import.html", {"form": form})


def _member(request, pk):
    return get_object_or_404(User, pk=pk, profile__school=request.user.profile.school)


@roles("admin")
def user_reset(request, pk):
    u = _member(request, pk)
    if request.method != "POST":
        return HttpResponseForbidden()
    pw = make_password()
    u.set_password(pw)
    u.save()
    u.profile.must_change_password = True
    u.profile.save(update_fields=["must_change_password"])
    return render(request, "user_created.html", {"accounts": [(u, pw)], "reset": True})


@roles("admin")
def user_toggle(request, pk):
    u = _member(request, pk)
    if request.method == "POST" and u != request.user:
        u.is_active = not u.is_active
        u.save(update_fields=["is_active"])
    return redirect("school")
