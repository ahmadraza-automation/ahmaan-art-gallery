from django.db import migrations
from django.utils.text import slugify


SAMPLE_ARTWORKS = [
    {
        'title': 'Borrowed Sunlight',
        'artist': 'Leena Rahman',
        'category': 'painting',
        'description': 'A sample artwork for previewing the gallery layout. Replace this entry and image with your own work.',
        'image_url': 'https://images.unsplash.com/photo-1541961017774-22349e4a1262?auto=format&fit=crop&w=1600&q=85',
        'medium': 'Acrylic on canvas',
        'dimensions': '60 × 80 cm',
        'year': 2025,
        'is_featured': True,
    },
    {
        'title': 'After the Rain',
        'artist': 'Omar Shah',
        'category': 'painting',
        'description': 'A sample artwork for previewing the gallery layout. Replace this entry and image with your own work.',
        'image_url': 'https://images.unsplash.com/photo-1579783901586-d88db74b4fe4?auto=format&fit=crop&w=1100&q=85',
        'medium': 'Oil on linen',
        'dimensions': '50 × 70 cm',
        'year': 2024,
    },
    {
        'title': 'Soft Geometry',
        'artist': 'Mira Saleem',
        'category': 'mixed-media',
        'description': 'A sample artwork for previewing the gallery layout. Replace this entry and image with your own work.',
        'image_url': 'https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?auto=format&fit=crop&w=1100&q=85',
        'medium': 'Paper and pigment',
        'dimensions': '40 × 50 cm',
        'year': 2025,
    },
    {
        'title': 'Still, Blue',
        'artist': 'Daniyal Noor',
        'category': 'photography',
        'description': 'A sample artwork for previewing the gallery layout. Replace this entry and image with your own work.',
        'image_url': 'https://images.unsplash.com/photo-1549490349-8643362247b5?auto=format&fit=crop&w=1100&q=85',
        'medium': 'Archival pigment print',
        'dimensions': '30 × 40 cm',
        'year': 2024,
    },
]


def add_sample_artworks(apps, schema_editor):
    Artwork = apps.get_model('gallery', 'Artwork')
    for artwork in SAMPLE_ARTWORKS:
        Artwork.objects.get_or_create(slug=slugify(artwork['title']), defaults=artwork)


def remove_sample_artworks(apps, schema_editor):
    Artwork = apps.get_model('gallery', 'Artwork')
    Artwork.objects.filter(slug__in=[slugify(item['title']) for item in SAMPLE_ARTWORKS]).delete()


class Migration(migrations.Migration):
    dependencies = [('gallery', '0001_initial')]

    operations = [migrations.RunPython(add_sample_artworks, remove_sample_artworks)]