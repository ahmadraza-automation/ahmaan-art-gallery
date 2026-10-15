from django.core import mail
from django.test import TestCase

from core.models import SiteSettings


class SiteSettingsAdminContentTests(TestCase):
    def test_custom_values_render_on_home_footer_and_contact(self):
        SiteSettings.objects.create(
            gallery_name='Custom Gallery',
            tagline='Custom tagline',
            footer_email='owner@example.com',
            phone='123456789',
            google_maps_url='https://maps.example.com/custom',
            youtube_url='https://youtube.com/@custom',
            tiktok_url='https://tiktok.com/@custom',
            contact_location='Custom City, Pakistan',
            contact_hours='Custom hours',
            contact_intro='Custom intro',
            support_reply_hours='Custom support hours',
            offer_tab_label='Custom offer',
            offer_dialog_heading='Custom offer heading',
            footer_newsletter_heading='Custom heading',
            footer_newsletter_text='Custom newsletter text',
            whatsapp_number='923000000000',
        )

        response = self.client.get('/')
        self.assertContains(response, 'Custom Gallery')
        self.assertContains(response, 'Custom tagline')
        self.assertContains(response, 'owner@example.com')
        self.assertContains(response, 'Custom heading')
        self.assertContains(response, 'Custom newsletter text')
        self.assertContains(response, 'Custom offer')

        contact_response = self.client.get('/contact/')
        self.assertContains(contact_response, 'Custom City, Pakistan')
        self.assertContains(contact_response, 'Custom hours')
        self.assertContains(contact_response, 'Custom intro')
        self.assertContains(contact_response, '123456789')
        self.assertContains(contact_response, 'https://maps.example.com/custom')
        self.assertContains(contact_response, 'Custom support hours')
        self.assertContains(contact_response, 'https://youtube.com/@custom')
        self.assertContains(contact_response, 'https://tiktok.com/@custom')

    def test_empty_values_fall_back_to_existing_text(self):
        SiteSettings.objects.create()

        response = self.client.get('/')
        self.assertContains(response, 'Ahmaan Art Gallery')
        self.assertContains(response, 'Art to live with, and live around.')
        self.assertContains(response, 'hello@ahmaanartgallery.pk')
        self.assertContains(response, 'A little art in your inbox.')
        self.assertContains(response, 'Get 10% Off')
        self.assertContains(response, 'Get 10% off your first order')

        contact_response = self.client.get('/contact/')
        self.assertContains(contact_response, 'Lahore, Pakistan')
        self.assertContains(contact_response, 'Tue – Sat, 11:00 – 7:00')
        self.assertContains(contact_response, 'Ask us about a work, arrange a viewing')
        self.assertContains(contact_response, 'Monday to Saturday, 10 AM to 8 PM')

    def test_whatsapp_button_hidden_when_empty(self):
        SiteSettings.objects.create(whatsapp_number='')

        response = self.client.get('/')
        self.assertNotContains(response, 'class="whatsapp-float"')
        self.assertNotContains(response, 'https://wa.me/')

        contact_response = self.client.get('/contact/')
        self.assertNotContains(contact_response, 'https://wa.me/')

    def test_newsletter_sender_uses_settings_when_present(self):
        settings = SiteSettings.objects.create(
            newsletter_sender_name='Custom Sender',
            newsletter_sender_email='custom@example.com',
        )

        self.assertEqual(settings.newsletter_sender_name, 'Custom Sender')
        self.assertEqual(settings.newsletter_sender_email, 'custom@example.com')
        self.assertEqual(settings.get_newsletter_sender(), ('Custom Sender', 'custom@example.com'))

        settings.newsletter_sender_name = ''
        settings.newsletter_sender_email = ''
        self.assertEqual(settings.get_newsletter_sender(), ('Ahmaan Art Gallery', 'hello@ahmaanartgallery.pk'))
