from django.db import migrations


SAMPLE_DESCRIPTION = 'A sample artwork for previewing the gallery layout. Replace this entry and image with your own work.'
SAMPLE_CATEGORIES = {
	'Borrowed Sunlight': ('oil-painting', 'Oil on canvas'),
	'After the Rain': ('oil-painting', 'Oil on linen'),
	'Soft Geometry': ('handmade-sketch', 'Pencil and pigment on paper'),
	'Still, Blue': ('digital-art', 'Archival pigment print'),
}


def update_sample_categories(apps, schema_editor):
	Artwork = apps.get_model('gallery', 'Artwork')
	for title, (category, medium) in SAMPLE_CATEGORIES.items():
		Artwork.objects.filter(title=title, description=SAMPLE_DESCRIPTION).update(category=category, medium=medium)


class Migration(migrations.Migration):
	dependencies = [('gallery', '0005_order_payment_method')]

	operations = [migrations.RunPython(update_sample_categories, migrations.RunPython.noop)]