import tempfile
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch
from PIL import Image

from catalog.models import (
	Artist, Artwork, ArtworkBundle, ArtworkBundleItem, ArtworkImage, ArtworkOffer, Category, Collection,
	FrameOption, NotifyRequest, PriceRange, Review, Room, SizeOption, Wishlist,
)
from core.models import JournalPost, SiteSettings
from gallery.models import Artwork as LegacyArtwork, ArtworkCategory, LegacyWishlist
from orders.reservations import release_expired_reservations, reserve_unique_artwork
from orders.models import GiftCard, GiftCardRedemption, Order as CommerceOrder


class CatalogFoundationTests(TestCase):
	def test_seed_command_is_repeatable(self):
		call_command('seed_gallery', verbosity=0)
		first_category_count = Category.objects.count()
		call_command('seed_gallery', verbosity=0)
		second_category_count = Category.objects.count()

		self.assertEqual(Collection.objects.count(), 4)
		self.assertEqual(Artist.objects.count(), 3)
		self.assertEqual(first_category_count, second_category_count)
		self.assertEqual(Artwork.objects.count(), 12)
		self.assertEqual(Artwork.objects.filter(is_featured=True).count(), 3)
		self.assertTrue(all(artwork.mood_tagline for artwork in Artwork.objects.all()))

	def test_artist_upload_is_converted_to_webp_and_resized(self):
		image_buffer = BytesIO()
		Image.new('RGB', (3000, 1500), color='navy').save(image_buffer, format='JPEG')
		upload = SimpleUploadedFile('artist-photo.jpg', image_buffer.getvalue(), content_type='image/jpeg')

		with tempfile.TemporaryDirectory() as media_directory, override_settings(MEDIA_ROOT=media_directory):
			artist = Artist.objects.create(name='Upload Test Artist', photo=upload)
			self.assertTrue(artist.photo.name.endswith('.webp'))
			self.assertTrue(Path(media_directory, artist.photo.name).exists())
			self.assertTrue(Path(media_directory, 'artists', 'artist-photo-1200.webp').exists())
			with Image.open(artist.photo.path) as saved_image:
				self.assertEqual(saved_image.format, 'WEBP')
				self.assertEqual(saved_image.size, (2400, 1200))

	def test_unique_artwork_reservation_expires_and_releases(self):
		category = Category.objects.create(name='Test Painting', slug='test-painting')
		artist = Artist.objects.create(name='Reservation Artist', slug='reservation-artist')
		artwork = Artwork.objects.create(
			title='Reserved Work', slug='reserved-work', mood_tagline='A quiet study', story='An original work.',
			artist=artist, category=category, medium='Oil on canvas', base_price=1000,
		)
		now = timezone.now()
		expires_at = reserve_unique_artwork(artwork.pk, now=now)

		self.assertEqual(expires_at, now + timedelta(hours=24))
		self.assertIsNone(reserve_unique_artwork(artwork.pk, now=now))
		self.assertEqual(release_expired_reservations(now=expires_at), 1)
		artwork.refresh_from_db()
		self.assertEqual(artwork.status, Artwork.Status.AVAILABLE)
		self.assertIsNone(artwork.reserved_until)


class CatalogBrowsingTests(TestCase):
	def setUp(self):
		self.artist = Artist.objects.create(name='Sana Raza', slug='sana-raza', specialty='Oil and natural forms')
		self.category = Category.objects.create(name='Oil Paintings', slug='oil-paintings')
		self.collection = Collection.objects.create(name='Quiet Landscapes', slug='quiet-landscapes')
		self.artwork = Artwork.objects.create(
			title='Quiet Courtyard', slug='quiet-courtyard', mood_tagline='A little calm at dusk.',
			story='Layered color holds the last light of day.', artist=self.artist, category=self.category,
			medium='Oil on canvas', year=2025, width=40, height=50, base_price=25000,
			color_palette_tags=['indigo', 'warm white'], mood_tags=['calm', 'reflective'],
			space_tags=['home', 'gallery'], is_featured=True,
		)
		self.artwork.collections.add(self.collection)
		self.other_artwork = Artwork.objects.create(
			title='Garden After Rain', slug='garden-after-rain', mood_tagline='Green after weather.',
			story='A small garden study.', artist=self.artist, category=self.category,
			medium='Gouache on paper', year=2024, width=30, height=40, base_price=18000,
			color_palette_tags=['sage', 'umber'], mood_tags=['warm'], space_tags=['cafe'],
		)
		self.size = SizeOption.objects.create(name='Medium', width=30, height=40, price_modifier=3000)
		self.frame = FrameOption.objects.create(name='Black frame', price_modifier=2000)

	def test_shop_filters_without_full_reload_for_htmx(self):
		response = self.client.get('/shop/?category=oil-paintings&color=indigo&min_price=0&max_price=25000', HTTP_HX_REQUEST='true')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Quiet Courtyard')
		self.assertNotContains(response, 'Garden After Rain')
		self.assertContains(response, 'Category: Oil Paintings')
		self.assertNotContains(response, 'From: 0')
		self.assertNotContains(response, 'To: 25000')

	def test_sorting_supports_price_and_title_orders(self):
		response = self.client.get('/shop/?sort=price-low-high')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(list(response.context['page_obj'].object_list), [self.other_artwork, self.artwork])

	def test_collection_and_artist_pages_render_their_work(self):
		for path in ('/collections/', '/collections/quiet-landscapes/', '/artists/sana-raza/'):
			with self.subTest(path=path):
				response = self.client.get(path)
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, 'Quiet Courtyard')

	def test_artist_directory_profile_city_interview_and_breadcrumbs(self):
		self.artist.city = 'Lahore'
		article = JournalPost.objects.create(
			title='In the studio with Sana', slug='in-the-studio-with-sana',
			excerpt='A conversation about process.', body='Studio notes.', is_published=True,
			category=JournalPost.Category.ARTIST_INTERVIEWS,
		)
		self.artist.interview_article = article
		self.artist.save()

		listing = self.client.get('/artists/')
		profile = self.client.get('/artists/sana-raza/')

		self.assertEqual(listing.status_code, 200)
		self.assertContains(listing, 'Our Artists')
		self.assertContains(listing, 'Lahore')
		self.assertEqual(profile.status_code, 200)
		self.assertContains(profile, 'Lahore')
		self.assertContains(profile, 'Read the artist interview')
		self.assertContains(profile, 'BreadcrumbList')
		self.assertContains(profile, '"@type":"Person"')

	def test_homepage_discovery_sections_use_rooms_ranges_and_featured_collections(self):
		self.collection.is_featured = True
		self.collection.save(update_fields=['is_featured'])
		response = self.client.get('/')

		self.assertContains(response, 'Shop by Room')
		self.assertContains(response, 'Dining Room')
		self.assertContains(response, 'Shop Dining Room Art')
		self.assertContains(response, 'Shop by Price')
		self.assertContains(response, 'Under PKR 15,000')
		self.assertContains(response, 'Curator Favorites')
		self.assertContains(response, '/collections/quiet-landscapes/')
		self.assertContains(response, 'New This Week')
		self.assertContains(response, 'Quiet Courtyard')

	def test_room_listing_filters_by_room_and_has_seo_metadata(self):
		room = Room.objects.get(slug='dining-room')
		room.artworks.add(self.artwork)
		response = self.client.get('/rooms/dining-room/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Quiet Courtyard')
		self.assertContains(response, '<title>Dining Room Art | Ahmaan Art Gallery Pakistan</title>')
		self.assertContains(response, 'rel="canonical" href="http://127.0.0.1:8000/rooms/dining-room/"')
		self.assertEqual(self.client.get('/new-arrivals/').status_code, 200)
		self.assertContains(self.client.get('/sitemap.xml'), '/rooms/dining-room/')
		self.assertContains(self.client.get('/sitemap.xml'), '/new-arrivals/')

	def test_new_arrivals_cards_show_product_details_and_actions(self):
		response = self.client.get('/new-arrivals/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Quiet Courtyard')
		self.assertContains(response, 'Sana Raza')
		self.assertContains(response, 'Oil on canvas')
		self.assertContains(response, '40 × 50 cm')
		self.assertContains(response, 'PKR 25000')
		self.assertContains(response, 'wishlist')
		self.assertContains(response, 'Choose options for Quiet Courtyard')

	def test_price_range_buttons_link_to_existing_catalog_filter(self):
		self.other_artwork.base_price = 14000
		self.other_artwork.save(update_fields=['base_price'])
		price_range = PriceRange.objects.get(label='Under PKR 15,000')
		self.assertEqual(price_range.minimum_price, 0)
		response = self.client.get('/shop/?min_price=0&max_price=14999')

		self.assertEqual(list(response.context['page_obj'].object_list), [self.other_artwork])

	def test_style_subject_and_dimension_filters_combine_with_existing_filters(self):
		self.artwork.style_tags = ['abstract']
		self.artwork.subject_tags = ['botanical']
		self.artwork.save(update_fields=['style_tags', 'subject_tags'])
		response = self.client.get(
			'/shop/?style=abstract&subject=botanical&size_band=medium&medium=Oil+on+canvas&color=indigo&availability=available&sort=newest',
			HTTP_HX_REQUEST='true',
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(list(response.context['page_obj'].object_list), [self.artwork])
		self.assertContains(response, 'Quiet Courtyard')

	def test_wishlist_toggle_uses_htmx_without_redirect(self):
		response = self.client.post(f'/wishlist/toggle/{self.artwork.pk}/', HTTP_HX_REQUEST='true')

		self.assertEqual(response.status_code, 204)
		self.assertEqual(response.headers['HX-Trigger'], '{"wishlistUpdated": {"added": true, "count": 1, "artwork_id": %d, "kind": "catalog"}}' % self.artwork.pk)

	def test_guest_wishlist_merges_immediately_after_login(self):
		user = get_user_model().objects.create_user(username='wishlistuser', password='TestPass!9284')
		legacy_category = ArtworkCategory.objects.create(name='Legacy Wish Test', slug='legacy-wish-test')
		legacy_artwork = LegacyArtwork.objects.create(
			title='Legacy Wish Work', slug='legacy-wish-work', artist='Legacy Artist',
			category=legacy_category, description='A legacy catalogue artwork.',
			image_url='https://example.com/legacy-wish.jpg',
		)
		self.client.post(f'/wishlist/toggle/{self.artwork.pk}/')
		self.client.post(f'/wishlist/legacy-toggle/{legacy_artwork.pk}/')

		response = self.client.post('/accounts/login/', {'username': user.username, 'password': 'TestPass!9284'})

		self.assertEqual(response.status_code, 302)
		self.assertTrue(Wishlist.objects.filter(user=user, artwork=self.artwork).exists())
		self.assertTrue(LegacyWishlist.objects.filter(user=user, artwork=legacy_artwork).exists())
		self.assertNotIn('catalog_wishlist', self.client.session)
		self.assertNotIn('legacy_wishlist', self.client.session)
		self.assertContains(self.client.get('/wishlist/'), 'Legacy Wish Work')

	def test_detail_page_has_htmx_wishlist_action_and_similar_artwork(self):
		peer_artist = Artist.objects.create(name='Peer Artist', slug='peer-artist')
		peer = Artwork.objects.create(
			title='Garden Study', slug='garden-study', mood_tagline='Green in the afternoon.',
			story='A small study of leaves.', artist=peer_artist, category=self.category,
			medium=self.artwork.medium, base_price=21000,
		)
		self.artwork.style_tags = ['quiet-modern']
		self.artwork.save(update_fields=['style_tags'])
		peer.style_tags = ['quiet-modern']
		peer.save(update_fields=['style_tags'])

		response = self.client.get(f'/artwork/{self.artwork.slug}/')

		self.assertContains(response, 'hx-post="/wishlist/toggle/%s/"' % self.artwork.pk)
		self.assertIn(peer, response.context['related_artworks'])

	def test_compare_is_session_based_limited_to_three_and_renders_dimensions(self):
		additional = []
		for index in range(2):
			additional.append(Artwork.objects.create(
				title=f'Compare Work {index}', slug=f'compare-work-{index}', mood_tagline='A thoughtful study.',
				story='An original work.', artist=self.artist, category=self.category,
				medium='Acrylic on board', width=90, height=100, base_price=32000,
			))
		artworks = [self.artwork, self.other_artwork, *additional]
		for artwork in artworks:
			self.client.post(f'/compare/toggle/{artwork.pk}/')

		self.assertEqual(self.client.session['catalog_compare'], [artwork.pk for artwork in artworks[:3]])
		response = self.client.get('/compare/')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Compare Work 0')
		self.assertContains(response, '90 × 100 cm')
		self.assertNotContains(response, 'Compare Work 1')

	def test_legacy_artwork_shares_compare_limit_and_comparison_table(self):
		legacy_category = ArtworkCategory.objects.create(name='Legacy Compare Test', slug='legacy-compare-test')
		legacy_artwork = LegacyArtwork.objects.create(
			title='Legacy Compare Work', slug='legacy-compare-work', artist='Legacy Artist',
			category=legacy_category, description='A legacy catalogue artwork.',
			image_url='https://example.com/legacy-compare.jpg', medium='Ink on paper',
			dimensions='20 x 30 cm', price=17000,
		)
		uncompared_legacy_artwork = LegacyArtwork.objects.create(
			title='Legacy Compare Extra', slug='legacy-compare-extra', artist='Other Legacy Artist',
			category=legacy_category, description='Another legacy catalogue artwork.',
			image_url='https://example.com/legacy-compare-extra.jpg', medium='Gouache on paper',
			dimensions='30 x 40 cm', price=19000,
		)
		self.client.post(f'/compare/toggle/{self.artwork.pk}/')
		self.client.post(f'/compare/toggle/{self.other_artwork.pk}/')
		self.client.post(f'/compare/legacy-toggle/{legacy_artwork.pk}/')
		self.client.post(f'/compare/legacy-toggle/{uncompared_legacy_artwork.pk}/')

		response = self.client.get('/compare/')
		self.assertContains(response, 'Quiet Courtyard')
		self.assertContains(response, 'Legacy Compare Work')
		self.assertContains(response, 'Legacy Artist')
		self.assertContains(response, '20 x 30 cm')
		self.assertContains(response, 'PKR 17000')
		self.assertNotContains(response, 'Legacy Compare Extra')
		self.assertEqual(len(response.context['compare_items']), 3)

		self.assertContains(self.client.get('/'), f'hx-post="/wishlist/legacy-toggle/{legacy_artwork.pk}/"')
		self.assertContains(self.client.get(f'/artwork/{legacy_artwork.slug}/'), f'hx-post="/wishlist/legacy-toggle/{legacy_artwork.pk}/"')

	def test_recently_viewed_remains_session_based(self):
		self.client.get(f'/artwork/{self.artwork.slug}/')
		response = self.client.get(f'/artwork/{self.other_artwork.slug}/')

		self.assertContains(response, 'Recently viewed')
		self.assertIn(self.artwork, response.context['recently_viewed'])

	def test_catalog_detail_and_quick_view_resolve_before_legacy_detail(self):
		response = self.client.get('/artwork/quiet-courtyard/')
		quick_view = self.client.get('/artwork/quiet-courtyard/?quick=1', HTTP_HX_REQUEST='true')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'A little calm at dusk.')
		self.assertContains(response, 'View in your room')
		self.assertEqual(quick_view.status_code, 200)
		self.assertContains(quick_view, 'Quiet Courtyard')

	def test_artist_and_collection_seo_overrides_render(self):
		self.artist.meta_title = 'Sana Raza Pakistani Oil Painter | Ahmaan Art Gallery'
		self.artist.meta_description = 'Discover Sana Raza original oil paintings in Pakistan.'
		self.artist.save()
		self.collection.meta_title = 'Quiet Landscapes Original Paintings | Ahmaan Art Gallery'
		self.collection.meta_description = 'Shop original landscape paintings in Pakistan.'
		self.collection.save()

		artist_response = self.client.get('/artists/sana-raza/')
		collection_response = self.client.get('/collections/quiet-landscapes/')

		self.assertContains(artist_response, '<title>Sana Raza Pakistani Oil Painter | Ahmaan Art Gallery</title>')
		self.assertContains(collection_response, '<title>Quiet Landscapes Original Paintings | Ahmaan Art Gallery</title>')

	def test_product_seo_overrides_render_in_metadata_and_schema(self):
		self.artwork.meta_title = 'Quiet Courtyard Oil Painting | Ahmaan Art Gallery'
		self.artwork.meta_description = 'Shop an original oil painting by Sana Raza, available in Lahore, Pakistan.'
		self.artwork.save()

		response = self.client.get('/artwork/quiet-courtyard/')

		self.assertContains(response, '<title>Quiet Courtyard Oil Painting | Ahmaan Art Gallery</title>', html=True)
		self.assertContains(response, 'name="description" content="Shop an original oil painting by Sana Raza, available in Lahore, Pakistan."')
		self.assertContains(response, 'rel="canonical" href="http://127.0.0.1:8000/artwork/quiet-courtyard/"')
		self.assertContains(response, '"@type":"Product"')

	def test_sitemap_and_robots_endpoints_are_available(self):
		sitemap = self.client.get('/sitemap.xml')
		self.assertEqual(sitemap.status_code, 200)
		self.assertContains(sitemap, '/artwork/quiet-courtyard/')
		self.assertContains(sitemap, '/artists/')
		self.assertContains(sitemap, '/for-designers/')
		self.assertContains(sitemap, '/shipping-payments/')
		self.assertContains(sitemap, '/cookie-policy/')
		robots = self.client.get('/robots.txt')
		self.assertEqual(robots.status_code, 200)
		self.assertContains(robots, 'Sitemap:')

	def test_instant_search_includes_artist_and_collection_results(self):
		collection_response = self.client.get('/search/?q=Quiet')
		artist_response = self.client.get('/search/?q=Sana')

		self.assertIn('Collection', [result['type'] for result in collection_response.json()['results']])
		self.assertIn('Artist', [result['type'] for result in artist_response.json()['results']])
		self.assertTrue(all('thumbnail' in result for result in collection_response.json()['results']))

	def test_similar_art_commission_link_prefills_the_request(self):
		response = self.client.get(f'/commission/?artwork={self.artwork.slug}')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, f'A piece in the spirit of {self.artwork.title}')

	def test_guest_wishlist_can_add_remove_and_render(self):
		added = self.client.post(f'/wishlist/toggle/{self.artwork.pk}/')
		self.assertEqual(added.json(), {'added': True, 'count': 1, 'artwork_id': self.artwork.pk, 'kind': 'catalog'})
		self.assertContains(self.client.get('/wishlist/'), 'Quiet Courtyard')
		removed = self.client.post(f'/wishlist/toggle/{self.artwork.pk}/')
		self.assertEqual(removed.json()['added'], False)
		self.assertEqual(self.client.session['catalog_wishlist'], [])

	def test_signed_in_wishlist_uses_database(self):
		user = get_user_model().objects.create_user(username='collector', password='TestPass!9284')
		self.client.force_login(user)
		response = self.client.post(f'/wishlist/toggle/{self.artwork.pk}/')

		self.assertTrue(response.json()['added'])
		self.assertTrue(Wishlist.objects.filter(user=user, artwork=self.artwork).exists())

	def test_sold_work_notification_and_review_are_saved(self):
		self.artwork.status = Artwork.Status.SOLD
		self.artwork.save(update_fields=['status'])
		notify_response = self.client.post(f'/artwork/{self.artwork.slug}/', {
			'action': 'notify', 'channel': 'email', 'email': 'collector@example.com',
		})
		review_response = self.client.post(f'/artwork/{self.artwork.slug}/', {
			'action': 'review', 'name': 'Gallery Visitor', 'rating': '5', 'text': 'A thoughtful piece.',
		})

		self.assertEqual(notify_response.status_code, 302)
		self.assertEqual(review_response.status_code, 302)
		self.assertTrue(NotifyRequest.objects.filter(artwork=self.artwork, email='collector@example.com').exists())
		self.assertTrue(Review.objects.filter(artwork=self.artwork, is_approved=False).exists())

	def test_product_customization_adds_catalog_line_to_session(self):
		response = self.client.post(f'/artwork/{self.artwork.slug}/add/', {
			'size': str(self.size.pk), 'frame': str(self.frame.pk), 'custom_text': 'Please include a note.',
		})

		self.assertEqual(response.status_code, 302)
		line = self.client.session['catalog_cart'][0]
		self.assertEqual(line['artwork_id'], self.artwork.pk)
		self.assertEqual(line['size_id'], self.size.pk)
		self.assertEqual(line['frame_id'], self.frame.pk)

	def test_catalog_cart_opens_the_shared_payment_checkout(self):
		self.client.post(f'/artwork/{self.artwork.slug}/add/', {
			'size': str(self.size.pk), 'frame': str(self.frame.pk), 'custom_text': 'Gift note',
		})

		response = self.client.get('/checkout/')

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'orders/checkout.html')
		self.assertContains(response, 'Quiet Courtyard')

	def test_artwork_offer_obeys_admin_minimum_and_sends_notification(self):
		SiteSettings.objects.create(minimum_offer_percent=80)
		with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ADMINS=(('Gallery', 'admin@example.com'),)):
			response = self.client.post(f'/artwork/{self.artwork.slug}/offer/', {
				'name': 'Ayesha Khan', 'phone': '+923001234567', 'email': 'ayesha@example.com', 'offer_price': '20000',
			})
			self.assertEqual(response.status_code, 302)
			self.assertTrue(ArtworkOffer.objects.filter(artwork=self.artwork, offer_price=20000).exists())
			from django.core import mail
			self.assertEqual(len(mail.outbox), 1)

		response = self.client.post(f'/artwork/{self.artwork.slug}/offer/', {
			'name': 'Ayesha Khan', 'phone': '+923001234567', 'email': 'ayesha@example.com', 'offer_price': '10000',
		})
		self.assertEqual(response.status_code, 302)
		self.assertEqual(ArtworkOffer.objects.count(), 1)

	def test_checkout_redeems_gift_card_once_and_applies_its_value(self):
		gift_card = GiftCard.objects.create(amount=10000, is_active=True, recipient_email='gift@example.com')
		session = self.client.session
		session['catalog_cart'] = [{'artwork_id': self.artwork.pk, 'quantity': 1}]
		session.save()
		with patch('orders.views.generate_order_certificate'):
			response = self.client.post('/checkout/', {
				'customer_name': 'Ayesha Khan', 'customer_email': 'ayesha@example.com', 'customer_phone': '+923001234567',
				'delivery_address': '12 Garden Road', 'city': 'Lahore', 'payment_method': 'cod',
				'coupon_code': '', 'gift_card_code': gift_card.code, 'customer_note': '',
			})

		self.assertEqual(response.status_code, 302)
		order = CommerceOrder.objects.get(customer_email='ayesha@example.com')
		self.assertEqual(order.total, 15000)
		gift_card.refresh_from_db()
		self.assertTrue(gift_card.is_redeemed)
		self.assertEqual(GiftCardRedemption.objects.get(gift_card=gift_card).amount_applied, 10000)

	def test_order_confirmation_renders_for_the_current_commerce_model(self):
		order = CommerceOrder.objects.create(
			reference='ORDER-SEO-123', customer_name='Gallery Collector',
			customer_email='collector@example.com', customer_phone='+923001234567',
			delivery_address='12 Garden Road', city='Lahore', subtotal=25000,
			total=25000,
		)
		order.items.create(artwork=self.artwork, title_at_order=self.artwork.title, unit_price=25000)
		session = self.client.session
		session['orders_last_reference'] = order.reference
		session.save()

		response = self.client.get(f'/checkout/order/{order.reference}/')

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'orders/confirmation.html')
		self.assertContains(response, order.reference)
		self.assertContains(response, 'Quiet Courtyard')

	def test_catalog_artwork_images_get_fallback_alt_text_and_srcset(self):
		image_buffer = BytesIO()
		Image.new('RGB', (900, 600), color='navy').save(image_buffer, format='JPEG')
		upload = SimpleUploadedFile('courtyard.jpg', image_buffer.getvalue(), content_type='image/jpeg')

		with tempfile.TemporaryDirectory() as media_directory, override_settings(MEDIA_ROOT=media_directory):
			image = ArtworkImage.objects.create(artwork=self.artwork, image=upload)
			response = self.client.get(f'/artwork/{self.artwork.slug}/')
			image.refresh_from_db()

			self.assertEqual(image.alt_text, 'Quiet Courtyard original artwork')
			self.assertContains(response, 'srcset=')
			self.assertContains(response, 'courtyard.webp 900w')
			self.assertNotContains(response, '2400w')

	def test_bundle_requires_two_or_three_works_and_a_discount(self):
		bundle = ArtworkBundle.objects.create(name='Quiet Pair', slug='quiet-pair', bundle_price=40000)
		ArtworkBundleItem.objects.create(bundle=bundle, artwork=self.artwork, order=0)
		ArtworkBundleItem.objects.create(bundle=bundle, artwork=self.other_artwork, order=1)
		bundle.refresh_from_db()
		bundle.full_clean()
		self.assertEqual(bundle.savings, 3000)
		self.assertEqual(self.client.get('/sets/quiet-pair/').status_code, 200)

	def test_bundle_item_save_rejects_a_non_discounted_pair(self):
		bundle = ArtworkBundle.objects.create(name='No Saving Pair', slug='no-saving-pair', bundle_price=43000)
		ArtworkBundleItem.objects.create(bundle=bundle, artwork=self.artwork, order=0)

		with self.assertRaises(ValidationError):
			ArtworkBundleItem.objects.create(bundle=bundle, artwork=self.other_artwork, order=1)