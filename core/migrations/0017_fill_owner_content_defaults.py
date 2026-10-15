from decimal import Decimal

from django.db import migrations


ABOUT_DESCRIPTION = (
    'Ahmaan Art Gallery is an online art gallery based in Bahawalpur, Pakistan. '
    'Founded by painter Mr Amaan Ahmad, who has been painting since 2020, the '
    'gallery brings original paintings and carefully chosen home décor together '
    'in one place. Every piece is selected to add warmth, character and a story '
    'to your space. Our aim is simple: to make beautiful, original art easy to '
    'discover and easy to own.'
)


def fill_empty_owner_defaults(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for site_settings in SiteSettings.objects.all():
        changed_fields = []
        defaults = {
            'packaging_text': 'Every artwork is packed in bubble wrap and a strong carton.',
            'shipping_partner': 'TCS / Leopards',
            'about_description': ABOUT_DESCRIPTION,
            'mission_text': 'To make original art a part of everyday homes, and to give every collector a piece with a story.',
        }
        for field_name, value in defaults.items():
            if not getattr(site_settings, field_name):
                setattr(site_settings, field_name, value)
                changed_fields.append(field_name)

        if not site_settings.flat_shipping_rate:
            site_settings.flat_shipping_rate = Decimal('300.00')
            changed_fields.append('flat_shipping_rate')
        if not site_settings.minimum_delivery_days:
            site_settings.minimum_delivery_days = 3
            changed_fields.append('minimum_delivery_days')
        if not site_settings.maximum_delivery_days:
            site_settings.maximum_delivery_days = 7
            changed_fields.append('maximum_delivery_days')
        if site_settings.payment_badge_cod is None:
            site_settings.payment_badge_cod = True
            changed_fields.append('payment_badge_cod')

        if changed_fields:
            site_settings.save(update_fields=changed_fields)


def reverse_fill_empty_owner_defaults(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_sitesettings_about_description_and_more'),
    ]

    operations = [
        migrations.RunPython(fill_empty_owner_defaults, reverse_fill_empty_owner_defaults),
    ]
