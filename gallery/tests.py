import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from PIL import Image

from core.models import SiteSettings, Testimonial
from .models import Artwork, ArtworkCategory, ContactInquiry, GalleryProfile, Order


class GalleryPagesTests(TestCase):
	def setUp(self):
		cache.clear()
		self.oil_category = ArtworkCategory.objects.get(slug=Artwork.Category.OIL_PAINTING)
		self.artwork = Artwork.objects.create(
			title='Quiet Garden',
			artist='Sample Artist',
			category=self.oil_category,
			description='A study in layered greens.',
			image_url='https://example.com/quiet-garden.jpg',
			price='1000.00',
			is_featured=True,
			is_popular=True,
		)

	def test_home_shows_featured_artwork(self):
		response = self.client.get('/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Quiet Garden')
		self.assertContains(response, 'Popular right now')

	def test_home_process_and_site_settings_counters_render(self):
		SiteSettings.objects.create(
			homepage_artists_count=12,
			homepage_artworks_count=84,
			homepage_cities_delivered_count=9,
			homepage_happy_collectors_count=67,
		)

		response = self.client.get('/')

		self.assertContains(response, 'How It Works')
		for label in ('Explore', 'Order', 'Secure Payment', 'Delivery'):
			self.assertContains(response, label)
		for count in ('12', '84', '9', '67'):
			self.assertContains(response, f'data-count="{count}"')
		self.assertContains(response, 'Free shipping / Worldwide delivery / WhatsApp par rabta karein')

	def test_existing_testimonial_shows_city_and_verified_mark(self):
		Testimonial.objects.create(
			name='Khurram', location='Lahore', quote='A beautiful addition.', is_published=True,
		)

		response = self.client.get('/')

		self.assertContains(response, 'Khurram, Lahore')
		self.assertContains(response, 'Verified collector')

	def test_announcement_can_be_disabled_and_payment_badges_follow_settings(self):
		SiteSettings.objects.create(
			announcement_bar_enabled=False,
			announcement_bar_text='Gallery update',
			bank_account_number='123456',
			jazzcash_number='03001234567',
			easypaisa_number='03007654321',
			payment_badge_jazzcash=False,
		)

		response = self.client.get('/')

		self.assertContains(response, 'class="announcement-strip" data-announcement-rotator aria-live="polite" aria-label="Gallery announcements" hidden')
		self.assertNotContains(response, 'Gallery update')
		self.assertContains(response, 'Cash on delivery')
		self.assertContains(response, 'Bank transfer')
		self.assertNotContains(response, '>JazzCash</span>')
		self.assertContains(response, 'Easypaisa')
		self.assertNotContains(response, 'Visa')
		self.assertNotContains(response, 'Mastercard')

	def test_starter_artworks_use_client_categories(self):
		response = self.client.get('/?category=oil-painting')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'After the Rain')
		self.assertNotContains(response, 'Still, Blue')

	def test_category_filter_limits_collection(self):
		Artwork.objects.create(
			title='Stone Form',
			artist='Sample Artist',
			category=ArtworkCategory.objects.get(slug=Artwork.Category.SCULPTURE),
			description='A small sculptural study.',
			image_url='https://example.com/stone-form.jpg',
		)

		response = self.client.get('/?category=oil-painting')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Quiet Garden')
		self.assertNotContains(response, 'Stone Form')

	def test_admin_added_category_can_be_used_and_filtered(self):
		category = ArtworkCategory.objects.create(name='Botanical Studies', slug='botanical-studies', sort_order=20)
		Artwork.objects.create(
			title='Wild Fern',
			artist='Sample Artist',
			category=category,
			description='A fern study.',
			image_url='https://example.com/fern.jpg',
		)

		response = self.client.get('/shop/?category=botanical-studies')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Wild Fern')
		self.assertNotContains(response, 'Quiet Garden')

	def test_artwork_detail_page_loads(self):
		response = self.client.get(f'/artwork/{self.artwork.slug}/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'A study in layered greens.')

	def test_legacy_artwork_seo_overrides_render(self):
		self.artwork.meta_title = 'Quiet Garden Oil Painting | Ahmaan Art Gallery'
		self.artwork.meta_description = 'Shop an original oil painting by Sample Artist in Pakistan.'
		self.artwork.save()

		response = self.client.get(f'/artwork/{self.artwork.slug}/')

		self.assertContains(response, '<title>Quiet Garden Oil Painting | Ahmaan Art Gallery</title>')
		self.assertContains(response, 'name="description" content="Shop an original oil painting by Sample Artist in Pakistan."')

	def test_contact_form_saves_an_inquiry(self):
		response = self.client.post('/contact/', {
			'name': 'Alex Visitor',
			'email': 'alex@example.com',
			'subject': 'Quiet Garden',
			'message': 'Could I arrange a viewing?',
		})

		self.assertRedirects(response, '/contact/')
		self.assertEqual(ContactInquiry.objects.count(), 1)
		self.assertEqual(ContactInquiry.objects.get().subject, 'Quiet Garden')

	def test_contact_honeypot_discards_bot_submission(self):
		response = self.client.post('/contact/', {
			'name': 'Bot', 'email': 'bot@example.com', 'subject': 'Spam',
			'message': 'Automated spam.', 'website': 'filled-by-bot',
		})

		self.assertRedirects(response, '/contact/')
		self.assertEqual(ContactInquiry.objects.count(), 0)

	def test_guest_can_place_cash_on_delivery_artwork_order(self):
		add_response = self.client.post('/cart/add/', {
			'artwork_id': self.artwork.pk,
			'size': Order.Size.LARGE,
			'frame': Order.Frame.WOOD,
			'custom_additions': 'Please use a natural wood frame.',
		})
		self.assertEqual(add_response.status_code, 302)

		response = self.client.post('/checkout/', {
			'customer_name': 'Alex Visitor',
			'customer_email': 'alex@example.com',
			'customer_phone': '+923001234567',
			'delivery_address': '12 Garden Road',
		})

		order = Order.objects.get()
		self.assertRedirects(response, f'/checkout/complete/{order.checkout_reference}/')
		self.assertEqual(order.order_type, Order.OrderType.ARTWORK)
		self.assertEqual(order.artwork, self.artwork)
		self.assertIsNone(order.user)
		self.assertEqual(order.frame, Order.Frame.WOOD)
		self.assertEqual(order.payment_method, Order.PaymentMethod.COD)
		self.assertEqual(order.price_at_order, 1500)
		self.assertEqual(order.custom_additions, 'Please use a natural wood frame.')
		confirmation = self.client.get(response.url)
		self.assertEqual(confirmation.status_code, 200)
		self.assertContains(confirmation, '12%20Garden%20Road')
		self.assertContains(confirmation, f'<title>Order {str(order.checkout_reference)[:8]} Received | Ahmaan Art Gallery</title>')

	def test_sold_artwork_cannot_be_ordered(self):
		self.artwork.is_available = False
		self.artwork.save(update_fields=['is_available'])

		response = self.client.post('/cart/add/', {'artwork_id': self.artwork.pk})

		self.assertEqual(response.status_code, 404)
		self.assertEqual(Order.objects.count(), 0)

	def test_cart_quantity_and_remove_actions(self):
		self.client.post('/cart/add/', {'artwork_id': self.artwork.pk, 'size': Order.Size.MEDIUM})
		line_id = self.client.session['gallery_cart'][0]['id']

		self.client.post(f'/cart/update/{line_id}/', {'quantity': '3'})
		self.assertEqual(self.client.session['gallery_cart'][0]['quantity'], 3)

		self.client.post(f'/cart/remove/{line_id}/', {'quantity': '0'})
		self.assertEqual(self.client.session['gallery_cart'], [])

	def test_custom_commission_accepts_reference_image(self):
		image_buffer = BytesIO()
		Image.new('RGB', (2, 2), color='white').save(image_buffer, format='PNG')
		upload = SimpleUploadedFile('portrait.png', image_buffer.getvalue(), content_type='image/png')

		with tempfile.TemporaryDirectory() as media_directory, override_settings(MEDIA_ROOT=media_directory):
			response = self.client.post('/commission/', {
				'customer_name': 'Alex Visitor',
				'customer_email': 'alex@example.com',
				'customer_phone': '+923001234567',
				'delivery_address': '12 Garden Road',
				'art_category': Artwork.Category.CUSTOM_PORTRAIT,
				'requested_title': 'Family portrait',
				'size': Order.Size.LARGE,
				'frame': Order.Frame.NONE,
				'custom_additions': 'Use a warm, natural palette.',
				'client_image': upload,
			})
			order = Order.objects.get()
			self.assertRedirects(response, f'/order/{order.pk}/complete/')
			self.assertEqual(order.order_type, Order.OrderType.COMMISSION)
			self.assertEqual(order.art_category, Artwork.Category.CUSTOM_PORTRAIT)
			self.assertTrue(order.client_image.name.endswith('portrait.png'))
			self.assertEqual(self.client.get(response.url).status_code, 200)

	def test_commission_honeypot_discards_bot_submission(self):
		response = self.client.post('/commission/', {
			'website': 'filled-by-bot',
			'customer_name': 'Bot', 'customer_email': 'bot@example.com',
			'customer_phone': '+923001234567', 'delivery_address': 'Nowhere',
		})

		self.assertRedirects(response, '/commission/')
		self.assertEqual(Order.objects.count(), 0)

	def test_new_pages_render(self):
		for path in ('/shop/', '/about/', '/commission/', '/accounts/login/', '/accounts/signup/'):
			with self.subTest(path=path):
				self.assertEqual(self.client.get(path).status_code, 200)

		self.assertRedirects(self.client.get('/account/'), '/accounts/login/?next=/account/')

	def test_about_page_shows_admin_managed_artist_bio(self):
		GalleryProfile.objects.create(
			artist_name='Amaan Ahmad',
			artist_background='Amaan works across traditional and digital media.',
			gallery_ethos='Art should feel personal and welcoming.',
		)

		response = self.client.get('/about/')

		self.assertContains(response, 'About Amaan Ahmad')
		self.assertContains(response, 'Amaan works across traditional and digital media.')
		self.assertContains(response, 'Art should feel personal and welcoming.')

	def test_instant_search_returns_matching_artwork(self):
		response = self.client.get('/search/?q=Quiet')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['results'][0]['title'], 'Quiet Garden')

	def test_profile_dashboard_requires_login_then_shows_order_history(self):
		user = get_user_model().objects.create_user('galleryuser')
		Order.objects.create(
			artwork=self.artwork,
			user=user,
			order_type=Order.OrderType.ARTWORK,
			art_category=self.oil_category.slug,
			requested_title=self.artwork.title,
			customer_name='Gallery User',
			customer_email='gallery@example.com',
			customer_phone='+923001234567',
			delivery_address='12 Garden Road',
			size=Order.Size.MEDIUM,
		)
		self.client.force_login(user)
		response = self.client.get('/account/')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Quiet Garden')

	def test_category_crud_is_available_in_admin(self):
		admin_user = get_user_model().objects.create_superuser('galleryadmin', 'admin@example.com', 'TestPass!9284')
		self.client.force_login(admin_user)
		self.assertEqual(self.client.get('/admin/gallery/artworkcategory/').status_code, 200)

	def test_visitor_can_create_an_account(self):
		response = self.client.post('/accounts/signup/', {
			'username': 'artvisitor',
			'password1': 'GalleryPass!9284',
			'password2': 'GalleryPass!9284',
		})

		self.assertRedirects(response, '/')
		self.assertTrue(self.client.session.get('_auth_user_id'))
