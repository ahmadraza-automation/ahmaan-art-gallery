from django.db import migrations
from django.utils.text import slugify


SAMPLE_TITLES = ('Borrowed Sunlight', 'After the Rain', 'Soft Geometry', 'Still, Blue')


def normalize_sample_slugs(apps, schema_editor):
    Artwork = apps.get_model('gallery', 'Artwork')
    for title in SAMPLE_TITLES:
        artwork = Artwork.objects.filter(title=title).first()
        if artwork:
            artwork.slug = slugify(title)
            artwork.save(update_fields=['slug'])


class Migration(migrations.Migration):
    dependencies = [('gallery', '0002_sample_artworks')]

    operations = [migrations.RunPython(normalize_sample_slugs, migrations.RunPython.noop)]