from django.db import migrations
from django.utils.text import slugify


PAINTING_CATEGORIES = [
    ('Abstract Art', 1),
    ('Calligraphy', 2),
    ('Aesthetic', 3),
    ('Animal', 4),
]
ACCESSORY_CATEGORIES = [
    ('Planters', 1),
    ('Decorated Mirrors', 2),
    ('Hanging Lamp', 3),
    ('Table Lamps', 4),
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    categories = [
        *[(name, 'paintings', order) for name, order in PAINTING_CATEGORIES],
        *[(name, 'accessories', order) for name, order in ACCESSORY_CATEGORIES],
    ]
    for name, group, order in categories:
        Category.objects.get_or_create(
            name=name,
            defaults={
                'slug': slugify(name),
                'group': group,
                'is_active': True,
                'order': order,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0011_category_group'),
    ]

    operations = [
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
