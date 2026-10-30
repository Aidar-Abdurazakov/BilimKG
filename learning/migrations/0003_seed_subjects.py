from django.db import migrations

# (slug, русское название, кыргызское название, с какого класса, по какой, цвет)
SUBJECTS = [
    ("matematika", "Математика", "Математика", 5, 6, "#2f6bff"),
    ("algebra", "Алгебра", "Алгебра", 7, 11, "#3b5bdb"),
    ("geometriya", "Геометрия", "Геометрия", 7, 11, "#5f3dc4"),
    ("fizika", "Физика", "Физика", 7, 11, "#1098ad"),
    ("himiya", "Химия", "Химия", 8, 11, "#37b24d"),
    ("prirodovedenie", "Природоведение", "Табият таануу", 5, 5, "#74b816"),
    ("biologiya", "Биология", "Биология", 6, 11, "#2f9e44"),
    ("geografiya", "География", "География", 5, 11, "#0c8599"),
    ("istoriya-kyrgyzstana", "История Кыргызстана", "Кыргызстандын тарыхы", 5, 11, "#c92a2a"),
    ("vsemirnaya-istoriya", "Всемирная история", "Дүйнөлүк тарых", 5, 11, "#a61e4d"),
    ("kyrgyz-tili", "Кыргызский язык", "Кыргыз тили", 5, 11, "#e03131"),
    ("kyrgyz-adabiyaty", "Кыргызская литература", "Кыргыз адабияты", 5, 11, "#f08c00"),
    ("russkiy-yazyk", "Русский язык", "Орус тили", 5, 11, "#1971c2"),
    ("russkaya-literatura", "Русская литература", "Орус адабияты", 5, 11, "#364fc7"),
    ("angliyskiy-yazyk", "Английский язык", "Англис тили", 5, 11, "#d6336c"),
    ("informatika", "Информатика", "Информатика", 5, 11, "#495057"),
    ("chelovek-i-obshchestvo", "Человек и общество", "Адам жана коом", 5, 11, "#862e9c"),
    ("muzyka", "Музыка", "Музыка", 5, 7, "#e64980"),
    ("izo", "Изобразительное искусство", "Сүрөт искусствосу", 5, 7, "#f76707"),
    ("tehnologiya", "Технология", "Технология", 5, 9, "#868e96"),
    ("fizkultura", "Физическая культура", "Дене тарбия", 5, 11, "#2b8a3e"),
    ("obzh", "Основы безопасности жизнедеятельности", "Жашоо коопсуздугунун негиздери", 5, 11, "#e8590c"),
    ("astronomiya", "Астрономия", "Астрономия", 11, 11, "#212529"),
    ("dopriz", "Допризывная подготовка", "Аскерге чейинки даярдык", 10, 11, "#5c940d"),
]


def seed(apps, schema_editor):
    Subject = apps.get_model("learning", "Subject")
    for slug, ru, ky, a, b, color in SUBJECTS:
        Subject.objects.update_or_create(slug=slug, defaults=dict(title=ru, title_ky=ky, grade_from=a, grade_to=b, color=color))


class Migration(migrations.Migration):
    dependencies = [("learning", "0002_schools_i18n")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
