import re
import secrets

from django.contrib.auth import get_user_model

LATIN_TO_CYR = str.maketrans("ABCEHKMOPTXabcehkmoptx", "АВСЕНКМОРТХАВСЕНКМОРТХ")
TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюяүөң", ["a","b","v","g","d","e","e","zh","z","i","y","k","l","m","n","o","p","r","s","t","u","f","kh","ts","ch","sh","sch","","y","","e","yu","ya","u","o","n"]))
PW_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def norm_class(value):
    """'7a', '7 А', '7А' -> '7А' (латиница-двойники заменяются кириллицей)."""
    return re.sub(r"\s+", "", (value or "")).translate(LATIN_TO_CYR).upper()


def translit(s):
    return "".join(TR.get(ch, ch) for ch in s.lower() if ch.isalnum())


def make_password(n=8):
    return "".join(secrets.choice(PW_ALPHABET) for _ in range(n))


def make_username(full_name):
    parts = full_name.split()
    base = ".".join(translit(p) for p in (parts[1:2] + parts[:1] if len(parts) > 1 else parts)) or "user"
    User, name, i = get_user_model(), base, 1
    while User.objects.filter(username=name).exists():
        i += 1
        name = f"{base}{i}"
    return name


def create_account(school, full_name, role, class_name="", password=None):
    """Создаёт пользователя в школе. Возвращает (user, пароль). Пароль временный: при первом входе его меняют."""
    User = get_user_model()
    parts = full_name.split()
    password = password or make_password()
    user = User.objects.create_user(make_username(full_name), password=password, last_name=parts[0][:150] if parts else "", first_name=" ".join(parts[1:])[:150])
    p = user.profile
    p.role, p.school, p.class_name, p.must_change_password = role, school, norm_class(class_name) if role == "student" else "", True
    p.save()
    return user, password
