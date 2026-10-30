from django.core.management.base import BaseCommand

from learning.models import School
from learning.utils import create_account, make_password


class Command(BaseCommand):
    help = "Создать школу и её администратора: python manage.py create_school 'Школа №1' 'Асанов Азамат'"

    def add_arguments(self, parser):
        parser.add_argument("name")
        parser.add_argument("admin_full_name")

    def handle(self, name, admin_full_name, **o):
        school = School.objects.create(name=name)
        user, pw = create_account(school, admin_full_name, "admin", password=make_password())
        self.stdout.write(self.style.SUCCESS(f"Школа «{name}» создана.\nЛогин админа: {user.username}\nВременный пароль: {pw}\n(при первом входе попросит сменить)"))
