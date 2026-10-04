from django.db import migrations


FAQS = (
	('buying', 'How do I purchase an artwork?', 'Open the artwork page, choose any listed options, and follow checkout. Contact the gallery if you would like help before ordering.'),
	('shipping', 'How is artwork delivered?', 'Works are packed with care and delivered across Pakistan. Timing and charges depend on the destination; contact the gallery for current details.'),
	('returns', 'What should I do if my artwork arrives damaged?', 'Contact the gallery within 48 hours and include photos so the team can review the issue and help resolve it.'),
	('commissions', 'Can I request a custom artwork?', 'Yes. Send your idea, preferred size, and any reference images through the commissions page, and the gallery will review your request.'),
	('framing', 'How can I choose a frame?', 'Available framing options appear on the artwork page. Contact the gallery if you would like help choosing a finish.'),
)


def add_faqs(apps, schema_editor):
	FAQ = apps.get_model('core', 'FAQ')
	for category, question, answer in FAQS:
		FAQ.objects.get_or_create(
			question=question,
			defaults={
				'category': category,
				'answer': answer,
				'is_published': True,
				'order': 0,
			},
		)


class Migration(migrations.Migration):
	dependencies = [('core', '0006_seed_homepage_trust_content')]
	operations = [migrations.RunPython(add_faqs, migrations.RunPython.noop)]
