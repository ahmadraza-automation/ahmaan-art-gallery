from django.db import migrations


def fill_owner_defaults(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for settings in SiteSettings.objects.all():
        if not settings.gallery_name:
            settings.gallery_name = 'Ahmaan Art Gallery'
        if not settings.tagline:
            settings.tagline = 'Art to live with, and live around.'
        if not settings.footer_email:
            settings.footer_email = 'hello@ahmaanartgallery.pk'
        if not settings.phone:
            settings.phone = ''
        if not settings.google_maps_url:
            settings.google_maps_url = ''
        if not settings.youtube_url:
            settings.youtube_url = ''
        if not settings.tiktok_url:
            settings.tiktok_url = ''
        if not settings.contact_location:
            settings.contact_location = 'Lahore, Pakistan'
        if not settings.contact_hours:
            settings.contact_hours = 'Tue – Sat, 11:00 – 7:00'
        if not settings.contact_intro:
            settings.contact_intro = "Ask us about a work, arrange a viewing, or simply start a conversation. We'll get back to you soon."
        if not settings.support_reply_hours:
            settings.support_reply_hours = 'Monday to Saturday, 10 AM to 8 PM'
        if not settings.offer_tab_label:
            settings.offer_tab_label = 'Get 10% off'
        if not settings.offer_dialog_heading:
            settings.offer_dialog_heading = 'Get 10% off your first order'
        if not settings.newsletter_sender_name:
            settings.newsletter_sender_name = 'Ahmaan Art Gallery'
        if not settings.newsletter_sender_email:
            settings.newsletter_sender_email = 'hello@ahmaanartgallery.pk'
        if not settings.footer_newsletter_heading:
            settings.footer_newsletter_heading = 'Notes from the gallery'
        if not settings.footer_newsletter_text:
            settings.footer_newsletter_text = 'A little art in your inbox.'
        settings.save(update_fields=[
            'gallery_name', 'tagline', 'footer_email', 'phone', 'google_maps_url',
            'youtube_url', 'tiktok_url', 'contact_location', 'contact_hours',
            'contact_intro', 'support_reply_hours', 'offer_tab_label', 'offer_dialog_heading',
            'newsletter_sender_name', 'newsletter_sender_email', 'footer_newsletter_heading',
            'footer_newsletter_text',
        ])


def reverse_fill_owner_defaults(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_sitesettings_contact_hours_and_more'),
    ]

    operations = [
        migrations.RunPython(fill_owner_defaults, reverse_fill_owner_defaults),
    ]
