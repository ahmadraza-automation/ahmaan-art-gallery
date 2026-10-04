from django.db import migrations


def seed_delivery_cities(apps, schema_editor):
    CityDeliveryTime = apps.get_model('core', 'CityDeliveryTime')
    cities = ('Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'Multan')
    for order, city in enumerate(cities):
        CityDeliveryTime.objects.get_or_create(
            city=city,
            defaults={'minimum_days': 3, 'maximum_days': 7, 'order': order},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0010_adslot_citydeliverytime_designerinquiry_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_delivery_cities, migrations.RunPython.noop),
    ]
