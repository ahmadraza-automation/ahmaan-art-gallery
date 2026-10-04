from django.db import migrations


TRUST_FEATURES = (
	('Original artwork', 'A considered selection of original works from independent artists.', '✳', 1),
	('Careful packing', 'Each piece is protected and prepared carefully for its journey.', '◇', 2),
	('Delivery support', 'Contact the gallery for help with delivery updates or order questions.', '↗', 3),
	('WhatsApp support', 'Message the gallery for help choosing a piece or placing an order.', 'WA', 4),
)


def add_homepage_content(apps, schema_editor):
	TrustFeature = apps.get_model('core', 'TrustFeature')
	BrandStory = apps.get_model('core', 'BrandStory')

	for title, description, icon, order in TRUST_FEATURES:
		TrustFeature.objects.get_or_create(
			title=title,
			defaults={'description': description, 'icon': icon, 'order': order, 'is_active': True},
		)

	BrandStory.objects.get_or_create(
		heading='Made to meet you where you are.',
		defaults={
			'story': 'We bring together original work by artists who notice the details others pass by. Each piece is chosen for its honesty, its craft, and the feeling it leaves in a room.',
			'button_text': 'The story behind the gallery',
			'is_active': True,
		},
	)


class Migration(migrations.Migration):
	dependencies = [('core', '0005_brandstory_pressmention_trustfeature_faq_category_and_more')]
	operations = [migrations.RunPython(add_homepage_content, migrations.RunPython.noop)]
