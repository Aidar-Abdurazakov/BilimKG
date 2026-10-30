import json
from pathlib import Path

from django.core.management.base import BaseCommand

from learning.models import Assignment, Question, Quiz, School, Subject, Topic
from learning.utils import create_account

MAP = {"m1": ("algebra", 7), "p1": ("fizika", 7), "i1": ("informatika", 7)}


class Command(BaseCommand):
    help = "Демо: общая библиотека тем/тестов + демо-школа с админом, учителем и учениками"

    def handle(self, **o):
        for t in json.loads((Path(__file__).resolve().parents[2] / "demo_topics.json").read_text(encoding="utf-8")):
            slug, grade = MAP[t["id"]]
            subj = Subject.objects.get(slug=slug)
            topic, new = Topic.objects.get_or_create(school=None, subject=subj, title=t["title"], defaults=dict(grade=grade, content=t["text"]))
            if new:
                quiz = Quiz.objects.create(school=None, subject=subj, topic=topic, title=f"Тест: {t['title']}", grade=grade)
                for i, q in enumerate(t["q"], 1):
                    Question.objects.create(quiz=quiz, text=q["t"], option_a=q["o"][0], option_b=q["o"][1], option_c=q["o"][2], option_d=q["o"][3], correct_option="ABCD"[q["a"]], order=i)
        school, new = School.objects.get_or_create(name="Демо-школа №1")
        if new:
            pw = "Demo12345"
            out = []
            for full, role, cls in [("Директоров Админ", "admin", ""), ("Асанова Айгуль", "teacher", ""), ("Тургунов Бекзат", "student", "7А"), ("Маратова Айдана", "student", "7А"), ("Исаков Нурлан", "student", "7Б")]:
                u, _ = create_account(school, full, role, cls, password=pw)
                u.profile.must_change_password = False
                u.profile.save()
                out.append(f"{role:8} {u.username:22} {pw}")
            Assignment.objects.create(school=school, subject=Subject.objects.get(slug="algebra"), grade=7, class_name="7А", title="Контрольная №1: уравнения", description="Решите на листочке: 1) 3x+6=0  2) 5x-10=15  3) 2(x+3)=14. Сфотографируйте работу и загрузите.")
            self.stdout.write("Демо-аккаунты (логин / пароль):\n" + "\n".join(out))
        self.stdout.write(self.style.SUCCESS("Демо-данные готовы."))
