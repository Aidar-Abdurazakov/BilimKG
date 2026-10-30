from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from .models import Assignment, Question, Quiz, School, Topic
from .utils import norm_class

DT = {"type": "datetime-local"}
DT_FMT = "%Y-%m-%dT%H:%M"


def dt_field(label):
    return forms.DateTimeField(label=label, required=False, widget=forms.DateTimeInput(attrs=DT, format=DT_FMT), input_formats=[DT_FMT, "%Y-%m-%d %H:%M"])


class ClassNameMixin:
    def clean_class_name(self):
        return norm_class(self.cleaned_data.get("class_name"))


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ["subject", "grade", "title", "content"]
        widgets = {"content": forms.Textarea(attrs={"rows": 12})}

    def clean_grade(self):
        g = self.cleaned_data["grade"]
        if not 5 <= g <= 11:
            raise forms.ValidationError(_("Класс от 5 до 11"))
        return g


class QuizForm(ClassNameMixin, TopicForm):
    closes_at = dt_field(_("Закрыть (дедлайн)"))
    opens_at = dt_field(_("Открыть с"))

    class Meta:
        model = Quiz
        fields = ["subject", "grade", "title", "class_name", "opens_at", "closes_at", "duration_minutes"]


class AssignmentForm(ClassNameMixin, TopicForm):
    deadline = dt_field(_("Срок сдачи"))

    class Meta:
        model = Assignment
        fields = ["subject", "grade", "title", "description", "class_name", "deadline"]
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}


QuestionFormSet = inlineformset_factory(
    Quiz, Question, extra=3, can_delete=True, min_num=1, validate_min=True,
    fields=["text", "option_a", "option_b", "option_c", "option_d", "correct_option"],
    widgets={"text": forms.Textarea(attrs={"rows": 2})},
)


class UserAddForm(forms.Form):
    full_name = forms.CharField(label=_("Фамилия и имя"), max_length=150)
    role = forms.ChoiceField(label=_("Роль"), choices=[("student", _("Ученик")), ("teacher", _("Учитель")), ("admin", _("Админ школы"))])
    class_name = forms.CharField(label=_("Класс (например 7А)"), max_length=40, required=False)

    def clean(self):
        d = super().clean()
        if d.get("role") == "student" and not norm_class(d.get("class_name")):
            self.add_error("class_name", _("Укажите класс ученика"))
        return d


class ImportForm(forms.Form):
    role = forms.ChoiceField(label=_("Роль"), choices=[("student", _("Ученик")), ("teacher", _("Учитель"))])
    lines = forms.CharField(label=_("Список: Фамилия Имя, класс — по одному в строке"), widget=forms.Textarea(attrs={"rows": 10, "placeholder": "Тургунов Бекзат, 7А\nМаратова Айдана, 7А"}))


class SchoolSetupForm(forms.Form):
    school_name = forms.CharField(label=_("Название школы"), max_length=180)
    admin_full_name = forms.CharField(label=_("ФИО администратора школы"), max_length=150)

    def clean_school_name(self):
        name = self.cleaned_data["school_name"].strip()
        if School.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(_("Школа с таким названием уже существует."))
        return name
