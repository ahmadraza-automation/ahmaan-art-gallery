from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from catalog.models import Artist, Artwork, Collection, Room
from core.models import JournalPost
from gallery.models import Artwork as LegacyArtwork


class PublicPagesSitemap(Sitemap):
	protocol = 'https'
	priority = 0.6
	changefreq = 'monthly'
	page_names = (
		'gallery:home',
		'gallery:shop',
		'gallery:artists',
		'gallery:collections',
		'gallery:new_arrivals',
		'gallery:about',
		'gallery:contact',
		'gallery:commission',
		'core:art_match',
		'core:for_designers',
		'core:shipping_payments',
		'core:cookie_policy',
		'core:quiz',
		'orders:gift_cards',
		'core:journal_index',
		'core:faq',
		'core:shipping',
		'core:returns',
		'core:privacy',
		'core:terms',
	)

	def items(self):
		return self.page_names

	def location(self, item):
		return reverse(item)


class ArtworkSitemap(Sitemap):
	protocol = 'https'
	changefreq = 'weekly'
	priority = 0.8

	def items(self):
		return Artwork.objects.filter(status__in=(Artwork.Status.AVAILABLE, Artwork.Status.SOLD)).select_related('artist', 'category')

	def lastmod(self, item):
		return item.updated_at

	def location(self, item):
		return reverse('gallery:artwork_detail', kwargs={'slug': item.slug})


class LegacyArtworkSitemap(Sitemap):
	protocol = 'https'
	changefreq = 'weekly'
	priority = 0.8

	def items(self):
		catalog_slugs = Artwork.objects.values_list('slug', flat=True)
		return LegacyArtwork.objects.filter(is_available=True).exclude(slug__in=catalog_slugs).select_related('category')

	def lastmod(self, item):
		return item.created_at

	def location(self, item):
		return reverse('gallery:artwork_detail', kwargs={'slug': item.slug})


class ArtistSitemap(Sitemap):
	protocol = 'https'
	priority = 0.6

	def items(self):
		return Artist.objects.all()

	def location(self, item):
		return reverse('gallery:artist_detail', kwargs={'slug': item.slug})


class CollectionSitemap(Sitemap):
	protocol = 'https'
	priority = 0.6

	def items(self):
		return Collection.objects.filter(artworks__status__in=(Artwork.Status.AVAILABLE, Artwork.Status.SOLD)).distinct()

	def location(self, item):
		return reverse('gallery:collection_detail', kwargs={'slug': item.slug})


class RoomSitemap(Sitemap):
	protocol = 'https'
	priority = 0.6

	def items(self):
		return Room.objects.filter(is_active=True)

	def location(self, item):
		return reverse('gallery:room_detail', kwargs={'slug': item.slug})


class JournalSitemap(Sitemap):
	protocol = 'https'
	priority = 0.5
	changefreq = 'monthly'

	def items(self):
		from django.utils import timezone
		return JournalPost.objects.filter(is_published=True, published_at__lte=timezone.now())

	def lastmod(self, item):
		return item.published_at

	def location(self, item):
		return reverse('core:journal_detail', kwargs={'slug': item.slug})


sitemaps = {
	'pages': PublicPagesSitemap,
	'artworks': ArtworkSitemap,
	'legacy-artworks': LegacyArtworkSitemap,
	'artists': ArtistSitemap,
	'collections': CollectionSitemap,
	'rooms': RoomSitemap,
	'journal': JournalSitemap,
}
