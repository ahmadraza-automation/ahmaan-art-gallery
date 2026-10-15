from django.test import TestCase

from core.models import SiteSettings


class SiteSettingsContentTests(TestCase):
    def test_about_description_uses_custom_value_and_legacy_fallback(self):
        settings = SiteSettings.objects.create(about_description='A custom About description.')
        response = self.client.get('/about/')
        self.assertContains(response, 'A custom About description.')

        settings.about_description = ''
        settings.save(update_fields=['about_description'])
        response = self.client.get('/about/')
        self.assertContains(response, 'Ahmaan Art Gallery brings original artwork and the people who connect with it a little closer.')

    def test_returns_policy_uses_custom_value_and_legacy_fallback(self):
        settings = SiteSettings.objects.create(returns_policy='Custom returns policy.')
        response = self.client.get('/returns/')
        self.assertContains(response, 'Custom returns policy.')

        settings.returns_policy = ''
        settings.save(update_fields=['returns_policy'])
        response = self.client.get('/returns/')
        self.assertContains(response, 'If a work arrives damaged or significantly differs from the description')

    def test_packaging_text_uses_custom_value_and_legacy_fallback(self):
        settings = SiteSettings.objects.create(packaging_text='Custom packaging details.')
        response = self.client.get('/shipping-payments/')
        self.assertContains(response, 'Custom packaging details.')

        settings.packaging_text = ''
        settings.save(update_fields=['packaging_text'])
        response = self.client.get('/shipping-payments/')
        self.assertContains(response, 'Delivery is available across Pakistan. Our team confirms the destination and estimated arrival before dispatch.')

    def test_payment_description_uses_custom_value_and_legacy_fallback(self):
        settings = SiteSettings.objects.create(cod_description='Custom cash-on-delivery terms.')
        response = self.client.get('/shipping-payments/')
        self.assertContains(response, 'Custom cash-on-delivery terms.')

        settings.cod_description = ''
        settings.save(update_fields=['cod_description'])
        response = self.client.get('/shipping-payments/')
        self.assertContains(response, 'Cash on delivery is available for eligible orders and locations.')

    def test_commission_details_render_only_when_set(self):
        response = self.client.get('/commission/')
        self.assertNotContains(response, 'Minimum price:')
        self.assertNotContains(response, 'Completion time:')
        self.assertNotContains(response, 'Advance:')
        self.assertContains(response, 'Choose a size and frame, describe your additions')

        SiteSettings.objects.create(
            commission_minimum_price='5000.00',
            commission_completion_time='Three to four weeks',
            commission_advance_percent=30,
        )
        response = self.client.get('/commission/')
        self.assertContains(response, 'Minimum price: PKR 5000')
        self.assertContains(response, 'Completion time: Three to four weeks')
        self.assertContains(response, 'Advance: 30%')
