from django.db import migrations


LEGACY_CATEGORY_SLUGS = ('painting', 'sculpture', 'photography', 'mixed-media')


def curate_categories(apps, schema_editor):
	ArtworkCategory = apps.get_model('gallery', 'ArtworkCategory')
	ArtworkCategory.objects.get_or_create(
		slug='bespoke-works',
		defaults={'name': 'Bespoke Works', 'sort_order': 5, 'is_active': True},
	)
	ArtworkCategory.objects.filter(slug__in=LEGACY_CATEGORY_SLUGS).update(is_active=False)


class Migration(migrations.Migration):
	dependencies = [('gallery', '0008_artworkcategory_order_checkout_reference_and_more')]

	operations = [migrations.RunPython(curate_categories, migrations.RunPython.noop)]