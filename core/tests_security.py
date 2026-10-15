from io import BytesIO
import importlib
import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from PIL import Image

from gallery.forms import CommissionRequestForm
from gallery.models import ArtworkCategory, Order as CommissionOrder
from orders.models import Order as CommerceOrder, OrderItem


class ProductionSettingsValidationTests(TestCase):
    def test_production_rejects_missing_and_weak_secret_keys(self):
        for secret_key in ('', 'short', 'django-insecure-' + 'x' * 60):
            with self.subTest(secret_key=secret_key[:16]), self.assertRaises(ImproperlyConfigured):
                with patch.dict(os.environ, {
                    'DJANGO_SECRET_KEY': secret_key,
                    'DJANGO_ALLOWED_HOSTS': 'gallery.example.com',
                }, clear=False):
                    importlib.import_module('config.settings_prod')

    def test_production_rejects_wildcard_hosts(self):
        for hosts in ('*', '*.example.com'):
            with self.subTest(hosts=hosts), self.assertRaises(ImproperlyConfigured):
                with patch.dict(os.environ, {
                    'DJANGO_SECRET_KEY': 'a' * 60,
                    'DJANGO_ALLOWED_HOSTS': hosts,
                }, clear=False):
                    importlib.import_module('config.settings_prod')


class AuthenticationSecurityTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_login_is_rate_limited_after_five_failed_attempts(self):
        for attempt in range(5):
            response = self.client.post('/accounts/login/', {
                'username': 'unknown-collector',
                'password': 'wrong-password',
            }, REMOTE_ADDR='192.0.2.21')
            self.assertNotEqual(response.status_code, 429, msg=f'Attempt {attempt + 1} was blocked early')

        response = self.client.post('/accounts/login/', {
            'username': 'unknown-collector',
            'password': 'wrong-password',
        }, REMOTE_ADDR='192.0.2.21')
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'Too many attempts, try again in 15 minutes', status_code=429)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_is_generic_for_existing_and_unknown_email(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username='reset-collector', email='known@example.com', password='LongPassword!938')
        self.assertEqual(self.client.get('/accounts/password_reset/').status_code, 200)

        responses = []
        for email in ('known@example.com', 'unknown@example.com'):
            response = self.client.post('/accounts/password_reset/', {'email': email}, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'If an account matches that email address, password reset instructions have been sent.')
            self.assertNotContains(response, email)
            responses.append(response.content.decode())
        self.assertEqual(
            responses[0].count('If an account matches that email address, password reset instructions have been sent.'),
            responses[1].count('If an account matches that email address, password reset instructions have been sent.'),
        )
        self.assertEqual(self.client.get('/accounts/password_reset/done/').status_code, 200)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        confirm_url = f'/accounts/reset/{uid}/{token}/'
        confirm_response = self.client.get(confirm_url, follow=True)
        self.assertEqual(confirm_response.status_code, 200)
        password_form_url = confirm_response.request['PATH_INFO']
        complete_response = self.client.post(password_form_url, {
            'new_password1': 'NewLongPassword!938',
            'new_password2': 'NewLongPassword!938',
        }, follow=True)
        self.assertEqual(complete_response.status_code, 200)
        self.assertContains(complete_response, 'Your password has been changed.')


class CertificatePrivacyTests(TestCase):
    def test_certificate_shows_only_public_verification_details(self):
        order = CommerceOrder.objects.create(
            customer_name='Private Collector',
            customer_email='private-customer@example.com',
            customer_phone='5550001234',
            delivery_address='123 Private Street',
        )
        OrderItem.objects.create(order=order, title_at_order='Blue Garden', unit_price='25000.00')

        response = self.client.get(f'/verify/{order.certificate_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(order.certificate_id))
        self.assertContains(response, order.reference)
        self.assertContains(response, 'Blue Garden')
        self.assertNotContains(response, 'private-customer@example.com')
        self.assertNotContains(response, 'Private Collector')
        self.assertNotContains(response, '123 Private Street')

    def test_invalid_certificate_id_returns_polite_404(self):
        response = self.client.get('/verify/not-a-certificate-id/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Certificate not found', status_code=404)


class CommissionUploadSecurityTests(TestCase):
    def setUp(self):
        self.category = ArtworkCategory.objects.create(name='Security test art', slug='security-test-art')
        self.form_data = {
            'customer_name': 'Test Collector',
            'customer_email': 'collector@example.com',
            'customer_phone': '5550001234',
            'delivery_address': 'Test address',
            'art_category': self.category.slug,
            'size': CommissionOrder.Size.MEDIUM,
        }

    def test_oversized_commission_image_is_rejected(self):
        image_data = BytesIO()
        Image.new('RGB', (1700, 1700), (24, 45, 36)).save(image_data, format='BMP')
        upload = SimpleUploadedFile('large.png', image_data.getvalue(), content_type='image/png')
        form = CommissionRequestForm(data=self.form_data, files={'client_image': upload})

        self.assertFalse(form.is_valid())
        self.assertIn('8 MB or smaller', str(form.errors))

    def test_wrong_type_commission_image_is_rejected(self):
        image_data = BytesIO()
        Image.new('RGB', (20, 20), (24, 45, 36)).save(image_data, format='BMP')
        upload = SimpleUploadedFile('reference.png', image_data.getvalue(), content_type='image/png')
        form = CommissionRequestForm(data=self.form_data, files={'client_image': upload})

        self.assertFalse(form.is_valid())
        self.assertIn('client_image', form.errors)
