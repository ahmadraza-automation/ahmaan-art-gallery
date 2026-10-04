from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase, override_settings

from catalog.models import Artist, Artwork, Category, Room
from core.models import (
	AdSlot, ArtMatchQuestion, BrandStory, CityDeliveryTime, ConsultationRequest,
	CuratorAdviceBanner, CustomerReview, DesignerInquiry, FAQ, JournalPost,
	NewsletterSubscriber, PressMention, ShippingPaymentContent, TrustFeature,
	WelcomeOffer,
)
from orders.models import Coupon, GiftCard


class EditorialContentTests(TestCase):
	def test_journal_article_has_editorial_metadata_schema_and_reading_time(self):
		post = JournalPost.objects.create(
			title='A practical art care guide', slug='practical-art-care-guide',
			excerpt='Simple ways to care for a painting.', body='care ' * 401,
			category=JournalPost.Category.ART_CARE_TIPS, author='Gallery Conservator', is_published=True,
		)

		response = self.client.get(f'/journal/{post.slug}/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'BlogPosting')
		self.assertContains(response, 'BreadcrumbList')
		self.assertContains(response, '3 min read')
		self.assertContains(response, 'Gallery Conservator')
		self.assertContains(response, 'Art Care Tips')

	def test_designer_shipping_cookie_and_ads_txt_pages(self):
		content = ShippingPaymentContent.objects.create(cod_text='Cash on delivery across selected cities.')
		CityDeliveryTime.objects.update_or_create(city='Lahore', defaults={'minimum_days': 2, 'maximum_days': 4})
		self.assertEqual(self.client.get('/for-designers/').status_code, 200)
		response = self.client.post('/for-designers/', {
			'name': 'Sara Malik', 'company': 'Studio S', 'email': 'sara@example.com',
			'phone': '+923001234567', 'project_type': 'Hospitality', 'message': 'A hotel lobby project.',
		})
		self.assertEqual(response.status_code, 302)
		self.assertTrue(DesignerInquiry.objects.filter(email='sara@example.com').exists())
		shipping_response = self.client.get('/shipping-payments/')
		self.assertContains(shipping_response, content.cod_text)
		self.assertContains(shipping_response, 'Lahore')
		self.assertContains(shipping_response, '2–4 working days')
		self.assertContains(self.client.get('/cookie-policy/'), 'Cookie Policy')
		self.assertEqual(self.client.get('/ads.txt').content, b'')
		with override_settings(ADSENSE_ENABLED=True, ADSENSE_CLIENT_ID='ca-pub-123456'):
			self.assertContains(self.client.get('/ads.txt'), 'google.com, pub-123456, DIRECT')

	def test_ad_slots_require_enabled_settings_and_active_placement(self):
		AdSlot.objects.create(key='journal-list', name='Journal listing', slot_id='123456')
		JournalPost.objects.create(title='Published note', slug='published-note', excerpt='Short note.', is_published=True)
		self.assertNotContains(self.client.get('/journal/'), 'data-adsense-slot')
		with override_settings(ADSENSE_ENABLED=True, ADSENSE_CLIENT_ID='ca-pub-123456'):
			response = self.client.get('/journal/')
		self.assertContains(response, 'data-adsense-slot')
		self.assertContains(response, 'data-ad-slot="123456"')

	def test_seeded_homepage_content_renders(self):
		call_command('seed_gallery', verbosity=0)

		response = self.client.get('/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Latest from the journal')
		self.assertContains(response, 'A first look, with us')
		self.assertEqual(JournalPost.objects.filter(is_published=True).count(), 3)
		self.assertTrue(WelcomeOffer.objects.filter(is_active=True).exists())

	def test_newsletter_signup_normalizes_address_and_redirects_safely(self):
		response = self.client.post('/newsletter/', {
			'email': '  ARTIST@EXAMPLE.COM ',
			'next': 'https://outside.example/path',
		})

		self.assertRedirects(response, '/')
		self.assertTrue(NewsletterSubscriber.objects.filter(email='artist@example.com', is_active=True).exists())

	def test_newsletter_signup_rejects_invalid_address(self):
		response = self.client.post('/newsletter/', {'email': 'not-an-email', 'next': '/'})

		self.assertRedirects(response, '/')
		self.assertEqual(NewsletterSubscriber.objects.count(), 0)

	def test_newsletter_popup_creates_unique_discount_coupon(self):
		response = self.client.post('/newsletter/', {
			'email': 'vip@example.com',
			'next': '/',
			'discount_popup': '1',
		})

		self.assertRedirects(response, '/')
		self.assertTrue(NewsletterSubscriber.objects.filter(email='vip@example.com', is_active=True).exists())
		coupon = Coupon.objects.filter(discount_percent=10).order_by('-pk').first()
		self.assertIsNotNone(coupon)
		self.assertEqual(coupon.usage_limit, 1)
		first_code = coupon.code
		self.client.post('/newsletter/', {
			'email': 'vip@example.com',
			'next': '/',
			'discount_popup': '1',
		})
		self.assertEqual(Coupon.objects.filter(issued_to_email='vip@example.com').count(), 1)
		self.assertEqual(Coupon.objects.get(issued_to_email='vip@example.com').code, first_code)

	def test_quiz_page_is_available_at_the_short_url(self):
		ArtMatchQuestion.objects.get_or_create(key='room', defaults={'prompt': 'What room are you styling?', 'order': 1})
		response = self.client.get('/quiz/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Find the right piece for your room')

	def test_quiz_returns_catalog_artwork_matching_all_five_answers(self):
		answers = {
			'room': ('living-room', 'Living room'),
			'style': ('abstract', 'Abstract'),
			'color': ('indigo', 'Indigo'),
			'budget': ('middle', 'PKR 20,000 - 50,000'),
			'size': ('small', 'Small'),
		}
		post_data = {'action': 'quiz'}
		for order, (key, (value, label)) in enumerate(answers.items(), start=1):
			question, _ = ArtMatchQuestion.objects.get_or_create(key=key, defaults={'prompt': f'Choose {key}', 'order': order})
			question.is_active = True
			question.save(update_fields=['is_active'])
			option, _ = question.options.get_or_create(value=value, defaults={'label': label})
			post_data[f'question_{question.pk}'] = option.value
		budget_option = ArtMatchQuestion.objects.get(key='budget').options.get(value='middle')
		budget_option.minimum_price = 20000
		budget_option.maximum_price = 50000
		budget_option.save()
		artist = Artist.objects.create(name='Quiz Artist', slug='quiz-artist')
		category = Category.objects.create(name='Quiz Paintings', slug='quiz-paintings')
		room, _ = Room.objects.get_or_create(slug='living-room', defaults={'name': 'Living room'})
		artwork = Artwork.objects.create(
			title='Quiz Match', slug='quiz-match', mood_tagline='A quiet abstract.', story='An original painting.',
			artist=artist, category=category, medium='Acrylic', base_price=30000,
			style_tags=['abstract'], color_palette_tags=['indigo'], width=30, height=30,
		)
		artwork.rooms.add(room)

		response = self.client.post('/quiz/', post_data)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, artwork.title)
		self.assertContains(response, 'Your shortlist')

	def test_gift_card_request_is_saved_inactive_for_admin_fulfillment(self):
		self.assertEqual(self.client.get('/gift-cards/').status_code, 200)
		response = self.client.post('/gift-cards/', {
			'amount': '25000',
			'recipient_name': 'Ayesha Khan',
			'recipient_email': 'ayesha@example.com',
			'message': 'For your new home',
		})

		self.assertRedirects(response, '/gift-cards/')
		gift_card = GiftCard.objects.get(recipient_email='ayesha@example.com')
		self.assertEqual(gift_card.amount, 25000)
		self.assertTrue(gift_card.code)
		self.assertFalse(gift_card.is_active)

	def test_public_form_rate_limit_returns_too_many_requests(self):
		cache.clear()
		for _ in range(8):
			self.client.post('/contact/', {})

		response = self.client.post('/contact/', {})
		self.assertEqual(response.status_code, 429)

	def test_rate_limit_can_use_a_trusted_proxy_client_ip_header(self):
		cache.clear()
		with self.settings(RATE_LIMIT_CLIENT_IP_HEADER='HTTP_X_REAL_IP'):
			for _ in range(8):
				self.client.post('/contact/', {}, HTTP_X_REAL_IP='203.0.113.10')
			response = self.client.post('/contact/', {}, HTTP_X_REAL_IP='203.0.113.11')

		self.assertNotEqual(response.status_code, 429)

	def test_content_pages_and_journal_are_available(self):
		FAQ.objects.create(question='Can I commission a portrait?', answer='Yes. We can create a custom portrait.', is_published=True)
		JournalPost.objects.create(
			title='Notes on framing',
			slug='notes-on-framing',
			meta_title='Original Art Framing Guide | Ahmaan Journal',
			meta_description='Learn how to frame original art and paintings.',
			excerpt='A quick guide to choosing the right frame.',
			body='The right frame quietly brings a work to life.',
			is_published=True,
		)

		for path, expected in (
			('/journal/', 'Notes on framing'),
			('/journal/notes-on-framing/', 'The right frame quietly brings a work to life.'),
			('/faq/', 'Can I commission a portrait?'),
			('/shipping/', 'Shipping'),
			('/returns/', 'Returns'),
			('/privacy/', 'Privacy Policy'),
			('/terms/', 'Terms'),
		):
			with self.subTest(path=path):
				response = self.client.get(path)
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, expected)
		self.assertContains(self.client.get('/journal/notes-on-framing/'), '<title>Original Art Framing Guide | Ahmaan Journal</title>')

	def test_homepage_trust_content_is_admin_managed_and_press_strip_is_optional(self):
		TrustFeature.objects.create(title='Careful packing', description='Wrapped for its journey.', icon='box', order=1)
		BrandStory.objects.update(is_active=False)
		BrandStory.objects.create(heading='Made with care', story='An independent gallery in Lahore.')

		response = self.client.get('/')
		self.assertContains(response, 'Why Shop With Us')
		self.assertContains(response, 'Careful packing')
		self.assertContains(response, 'Made with care')
		self.assertGreaterEqual(TrustFeature.objects.filter(is_active=True).count(), 4)
		self.assertNotContains(response, 'As featured in')

		PressMention.objects.create(publication='Art & Home')
		self.assertContains(self.client.get('/'), 'As featured in')

	def test_collector_reviews_require_approval_and_can_be_submitted(self):
		response = self.client.post('/reviews/submit/', {
			'name': 'Ayesha Khan',
			'city': 'Lahore',
			'rating': '5',
			'title': 'A lovely addition',
			'text': 'The painting feels at home in our living room.',
		})
		self.assertRedirects(response, '/#customer-reviews', fetch_redirect_response=False)
		review = CustomerReview.objects.get()
		self.assertFalse(review.is_approved)
		self.assertNotContains(self.client.get('/'), 'A lovely addition')

		review.is_approved = True
		review.is_verified = True
		review.save()
		response = self.client.get('/')
		self.assertContains(response, 'What Our Collectors Are Saying')
		self.assertContains(response, 'A lovely addition')
		self.assertContains(response, 'Verified')
		self.assertContains(response, 'Lahore')

	def test_faq_categories_render_in_alpine_accordion_with_schema(self):
		FAQ.objects.create(
			category=FAQ.Category.SHIPPING,
			question='How is art delivered?',
			answer='Every work is packed with care.',
			is_published=True,
		)

		response = self.client.get('/faq/')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Shipping')
		self.assertContains(response, 'x-data=')
		self.assertContains(response, 'FAQPage')
		self.assertContains(response, 'canonical')
		self.assertContains(response, '<title>Frequently asked questions | Ahmaan Art Gallery Pakistan</title>')
		for category, label in FAQ.Category.choices:
			self.assertContains(response, label)
		self.assertEqual(self.client.get('/faqs/').status_code, 200)

	def test_curator_advice_page_and_form_are_available(self):
		room_question, _ = ArtMatchQuestion.objects.get_or_create(key='room', defaults={'prompt': 'What room are you styling?', 'order': 1})
		room_question.options.get_or_create(label='Living room', value='living-room')
		room_question.options.get_or_create(label='Bedroom', value='bedroom')
		budget_question, _ = ArtMatchQuestion.objects.get_or_create(key='budget', defaults={'prompt': 'What is your ideal budget?', 'order': 2})
		budget_question.options.get_or_create(label='PKR 25,000 - 50,000', value='25000-50000')
		CuratorAdviceBanner.objects.update_or_create(is_active=True, defaults={'heading': 'Need a second opinion?', 'text': 'Tell us about your room and what you love.'})

		response = self.client.get('/art-match/')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Find the right piece for your room')
		self.assertContains(response, 'Need a second opinion?')
		self.assertContains(response, 'canonical')
		self.assertContains(response, '<title>Art Match | Ahmaan Art Gallery Pakistan</title>')

		contact_response = self.client.post('/art-match/', {
			'name': 'Ayesha Khan',
			'phone': '+923001234567',
			'email': 'ayesha@example.com',
			'message': 'I need help choosing a painting for my living room.',
		})
		self.assertEqual(contact_response.status_code, 302)
		self.assertTrue(ConsultationRequest.objects.filter(email='ayesha@example.com').exists())
