from django.db import migrations


ROOMS = (
	('Dining Room', 'Find original work for meals and conversation.', 1),
	('Living Room', 'Make a gathering place for art and everyday life.', 2),
	('Kitchen', 'Bring a little color to the room where you cook.', 3),
	('Bedroom', 'Choose a quieter piece for a slower room.', 4),
)

PRICE_RANGES = (
	('Under PKR 15,000', 0, 14999, 1),
	('PKR 15,000-30,000', 15000, 30000, 2),
	('PKR 30,001-60,000', 30001, 60000, 3),
	('PKR 60,001 and above', 60001, None, 4),
)


def add_discovery_content(apps, schema_editor):
	Room = apps.get_model('catalog', 'Room')
	PriceRange = apps.get_model('catalog', 'PriceRange')

	for name, short_description, order in ROOMS:
		Room.objects.get_or_create(
			slug=name.lower().replace(' ', '-'),
			defaults={'name': name, 'short_description': short_description, 'order': order, 'is_active': True},
		)

	for label, minimum_price, maximum_price, order in PRICE_RANGES:
		PriceRange.objects.get_or_create(
			label=label,
			defaults={
				'minimum_price': minimum_price,
				'maximum_price': maximum_price,
				'order': order,
				'is_active': True,
			},
		)


class Migration(migrations.Migration):
	dependencies = [('catalog', '0004_pricerange_room_artwork_rooms')]
	operations = [migrations.RunPython(add_discovery_content, migrations.RunPython.noop)]
