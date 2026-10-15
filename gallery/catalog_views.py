from decimal import Decimal, InvalidOperation
import json
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.forms import ArtworkOfferForm, NotifyRequestForm, ReviewForm
from catalog.models import (
	Artist, Artwork, ArtworkBundle, ArtworkOffer,
	CanvasType, Category, Collection, FrameOption, NotifyRequest, Review,
	Room, SizeOption, Wishlist,
)
from core.models import AdSlot, SiteSettings
from core.seo import schema_json
from core.security import rate_limit
from gallery.models import Artwork as LegacyArtwork, ArtworkCategory, LegacyWishlist


class GalleryLoginView(LoginView):
	def form_valid(self, form):
		response = super().form_valid(form)
		guest_ids = self.request.session.pop('catalog_wishlist', [])
		if guest_ids:
			valid_ids = Artwork.objects.filter(pk__in=guest_ids).values_list('pk', flat=True)
			Wishlist.objects.bulk_create(
				[Wishlist(user=self.request.user, artwork_id=artwork_id) for artwork_id in valid_ids],
				ignore_conflicts=True,
			)
		legacy_ids = self.request.session.pop('legacy_wishlist', [])
		if legacy_ids:
			valid_legacy_ids = LegacyArtwork.objects.filter(pk__in=legacy_ids).values_list('pk', flat=True)
			LegacyWishlist.objects.bulk_create(
				[LegacyWishlist(user=self.request.user, artwork_id=artwork_id) for artwork_id in valid_legacy_ids],
				ignore_conflicts=True,
			)
		return response


def _htmx_event(event_name, detail, status=204):
	return HttpResponse(status=status, headers={'HX-Trigger': json.dumps({event_name: detail})})


def _safe_decimal(value):
	try:
		amount = Decimal(value)
		return amount if amount.is_finite() and amount >= 0 else None
	except (InvalidOperation, TypeError, ValueError):
		return None


def _query_without(request, key):
	query = request.GET.copy()
	query.pop(key, None)
	return f'?{query.urlencode()}' if query else '?'


def _available_filter_values(field):
	values = []
	for tags in Artwork.objects.values_list(field, flat=True).iterator():
		for tag in tags or []:
			if tag and tag not in values:
				values.append(tag)
	return sorted(values, key=str.casefold)


def shop(request):
	artworks = Artwork.objects.select_related('artist', 'category').prefetch_related('images', 'collections')
	filter_values = {
		'category': request.GET.get('category', '').strip(),
		'group': request.GET.get('group', '').strip(),
		'collection': request.GET.get('collection', '').strip(),
		'size': request.GET.get('size', '').strip(),
		'size_band': request.GET.get('size_band', '').strip(),
		'medium': request.GET.get('medium', '').strip(),
		'style': request.GET.get('style', '').strip(),
		'subject': request.GET.get('subject', '').strip(),
		'color': request.GET.get('color', '').strip(),
		'mood': request.GET.get('mood', '').strip(),
		'space': request.GET.get('space', '').strip(),
		'artist': request.GET.get('artist', '').strip(),
		'availability': request.GET.get('availability', '').strip(),
		'sort': request.GET.get('sort', 'featured').strip(),
	}
	minimum = _safe_decimal(request.GET.get('min_price', ''))
	maximum = _safe_decimal(request.GET.get('max_price', ''))
	if filter_values['group'] in {'paintings', 'accessories'}:
		artworks = artworks.filter(category__group=filter_values['group'])
	if filter_values['category']:
		artworks = artworks.filter(category__slug=filter_values['category'])
	if filter_values['collection']:
		artworks = artworks.filter(collections__slug=filter_values['collection'])
	if filter_values['artist']:
		artworks = artworks.filter(artist__slug=filter_values['artist'])
	if filter_values['medium']:
		artworks = artworks.filter(medium__iexact=filter_values['medium'])
	if filter_values['style']:
		artworks = artworks.filter(style_tags__icontains=filter_values['style'])
	if filter_values['subject']:
		artworks = artworks.filter(subject_tags__icontains=filter_values['subject'])
	if filter_values['color']:
		artworks = artworks.filter(color_palette_tags__icontains=filter_values['color'])
	if filter_values['mood']:
		artworks = artworks.filter(mood_tags__icontains=filter_values['mood'])
	if filter_values['space']:
		artworks = artworks.filter(space_tags__icontains=filter_values['space'])
	if filter_values['size_band'] == 'small':
		artworks = artworks.filter(width__lte=40, height__lte=40)
	elif filter_values['size_band'] == 'medium':
		artworks = artworks.filter(width__lte=80, height__lte=80).filter(Q(width__gt=40) | Q(height__gt=40))
	elif filter_values['size_band'] == 'large':
		artworks = artworks.filter(Q(width__gt=80) | Q(height__gt=80))
	if filter_values['availability'] in Artwork.Status.values:
		artworks = artworks.filter(status=filter_values['availability'])
	if minimum is not None:
		artworks = artworks.filter(base_price__gte=minimum)
	if maximum is not None:
		artworks = artworks.filter(base_price__lte=maximum)
	if filter_values['size']:
		selected_size = SizeOption.objects.filter(pk=filter_values['size'], is_active=True).first()
		if selected_size:
			if selected_size.width:
				artworks = artworks.filter(width__gte=selected_size.width)
			if selected_size.height:
				artworks = artworks.filter(height__gte=selected_size.height)

	sort_map = {
		'featured': ('-is_featured', '-created_at'),
		'best-selling': ('-is_best_seller', '-created_at'),
		'newest': ('-created_at',),
		'oldest': ('created_at',),
		'price-low-high': ('base_price', 'title'),
		'price-high-low': ('-base_price', 'title'),
		'a-z': ('title',),
		'z-a': ('-title',),
	}
	artworks = artworks.order_by(*sort_map.get(filter_values['sort'], sort_map['featured'])).distinct()
	max_price = Artwork.objects.order_by('-base_price').values_list('base_price', flat=True).first() or Decimal('100000')
	page_number = request.GET.get('page', '1')
	page_obj = Paginator(artworks, 12).get_page(page_number)

	active_filters = []
	filter_labels = {
		'category': ('Category', Category, 'name'),
		'group': ('Group', None, None),
		'collection': ('Collection', Collection, 'name'),
		'artist': ('Artist', Artist, 'name'),
		'size': ('Size', SizeOption, 'name'),
		'size_band': ('Artwork size', None, None),
		'medium': ('Medium', None, None),
		'style': ('Style', None, None),
		'subject': ('Subject', None, None),
		'color': ('Colour', None, None),
		'mood': ('Mood', None, None),
		'space': ('Space', None, None),
		'availability': ('Availability', None, None),
	}
	for key, (label, model, text_field) in filter_labels.items():
		value = filter_values.get(key)
		if value:
			lookup = model.objects.filter(slug=value).first() if model and key != 'size' else model.objects.filter(pk=value).first() if model else None
			active_filters.append({'key': key, 'label': label, 'value': getattr(lookup, text_field) if lookup and text_field else value, 'remove_url': _query_without(request, key)})
	for key, label, value in (('min_price', 'From', request.GET.get('min_price')), ('max_price', 'To', request.GET.get('max_price'))):
		if value:
			amount = _safe_decimal(value)
			if (key == 'min_price' and amount == 0) or (key == 'max_price' and amount == max_price):
				continue
			active_filters.append({'key': key, 'label': label, 'value': value, 'remove_url': _query_without(request, key)})

	legacy_fallback = False
	legacy_artworks = LegacyArtwork.objects.none()
	if filter_values['category'] and not Category.objects.filter(slug=filter_values['category']).exists():
		legacy_category = ArtworkCategory.objects.filter(slug=filter_values['category'], is_active=True).first()
		if legacy_category:
			legacy_fallback = True
			legacy_artworks = LegacyArtwork.objects.filter(category=legacy_category).select_related('category')

	context = {
		'seo_title': 'Original Paintings and Contemporary Art for Sale in Pakistan | Ahmaan Art Gallery',
		'seo_description': 'Shop original paintings, calligraphy, and contemporary art by Pakistani artists. Explore curated collections with secure delivery across Pakistan.',
		'page_obj': page_obj,
		'wishlist_ids': _wishlist_ids(request),
		'has_product_options': SizeOption.objects.filter(is_active=True).exists() or FrameOption.objects.filter(is_active=True).exists() or CanvasType.objects.filter(is_active=True).exists(),
		'filter_values': filter_values,
		'active_filters': active_filters,
		'categories': Category.objects.filter(is_active=True),
		'collections': Collection.objects.all(),
		'artists': Artist.objects.all(),
		'size_options': SizeOption.objects.filter(is_active=True),
		'mediums': Artwork.objects.order_by('medium').values_list('medium', flat=True).distinct(),
		'accessory_categories': Category.objects.filter(is_active=True, group='accessories').order_by('order', 'name'),
		'styles': _available_filter_values('style_tags'),
		'subjects': _available_filter_values('subject_tags'),
		'colors': _available_filter_values('color_palette_tags'),
		'moods': _available_filter_values('mood_tags'),
		'spaces': _available_filter_values('space_tags'),
		'size_bands': (('small', 'Small · up to 40 cm'), ('medium', 'Medium · 41-80 cm'), ('large', 'Large · over 80 cm')),
		'max_price': max_price,
		'min_price': request.GET.get('min_price', '0'),
		'max_price_value': request.GET.get('max_price', str(max_price)),
		'column_count': request.GET.get('columns', '3') if request.GET.get('columns') in ('2', '3', '4') else '3',
		'bundles': ArtworkBundle.objects.filter(is_active=True).annotate(item_count=Count('artworks')).filter(item_count__in=(2, 3))[:3],
		'legacy_fallback': legacy_fallback,
		'legacy_artworks': legacy_artworks,
		'item_count': page_obj.paginator.count + legacy_artworks.count(),
		'ad_slot': AdSlot.objects.filter(key='artwork-list', is_active=True).first() if settings.ADSENSE_ENABLED and settings.ADSENSE_CLIENT_ID else None,
		'breadcrumb_jsonld': schema_json({
			'@context': 'https://schema.org', '@type': 'BreadcrumbList',
			'itemListElement': [
				{'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': settings.PUBLIC_SITE_URL.rstrip('/') + '/'},
				{'@type': 'ListItem', 'position': 2, 'name': 'Artworks', 'item': settings.PUBLIC_SITE_URL.rstrip('/') + '/shop/'},
			],
		}),
	}
	if page_obj.has_next():
		query = request.GET.copy()
		query['page'] = page_obj.next_page_number()
		context['next_page_url'] = f'{request.path}?{urlencode(query, doseq=True)}'
	if request.headers.get('HX-Request') == 'true':
		if request.GET.get('page') and request.GET.get('page') != '1':
			return render(request, 'gallery/partials/_shop_cards.html', context)
		return render(request, 'gallery/partials/_shop_results.html', context)
	return render(request, 'gallery/shop.html', context)


def collections_index(request):
	collections = Collection.objects.annotate(artwork_count=Count('artworks')).order_by('order', 'name')
	return render(request, 'gallery/collections.html', {
		'collections': collections,
		'seo_title': 'Curated Original Art Collections | Ahmaan Art Gallery Pakistan',
		'seo_description': 'Explore curated collections of original paintings and contemporary art, thoughtfully selected for homes and collectors across Pakistan.',
	})


def collection_detail(request, slug):
	collection = get_object_or_404(Collection.objects.prefetch_related('artworks__images', 'artworks__artist'), slug=slug)
	artworks = collection.artworks.select_related('artist', 'category').prefetch_related('images')
	base_url = settings.PUBLIC_SITE_URL.rstrip('/')
	return render(request, 'gallery/collection_detail.html', {
		'collection': collection,
		'artworks': artworks,
		'seo_title': collection.meta_title or f'{collection.name} Original Art Collection | Ahmaan Art Gallery',
		'seo_description': collection.meta_description or collection.short_description or f'Discover original paintings and contemporary art in the {collection.name} collection at Ahmaan Art Gallery Pakistan.',
		'seo_image': f'{base_url}{collection.cover_image.url}' if collection.cover_image else '',
		'breadcrumb_jsonld': schema_json({
			'@context': 'https://schema.org', '@type': 'BreadcrumbList',
			'itemListElement': [
				{'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': base_url + '/'},
				{'@type': 'ListItem', 'position': 2, 'name': 'Collections', 'item': base_url + '/collections/'},
				{'@type': 'ListItem', 'position': 3, 'name': collection.name, 'item': f'{base_url}/collections/{collection.slug}/'},
			],
		}),
	})


def room_detail(request, slug):
	room = get_object_or_404(Room, slug=slug, is_active=True)
	artworks = room.artworks.filter(status=Artwork.Status.AVAILABLE).select_related('artist', 'category').prefetch_related('images', 'collections')
	return render(request, 'gallery/room_detail.html', {
		'room': room,
		'artworks': artworks,
		'wishlist_ids': _wishlist_ids(request),
		'seo_title': room.meta_title or f'{room.name} Art | Ahmaan Art Gallery Pakistan',
		'seo_description': room.meta_description or room.short_description or f'Explore original artwork selected for your {room.name.lower()} at Ahmaan Art Gallery.',
	})


def new_arrivals(request):
	artworks = Artwork.objects.filter(status=Artwork.Status.AVAILABLE).select_related('artist', 'category').prefetch_related('images', 'collections').order_by('-created_at')
	page_obj = Paginator(artworks, 12).get_page(request.GET.get('page', '1'))
	return render(request, 'gallery/new_arrivals.html', {
		'page_obj': page_obj,
		'wishlist_ids': _wishlist_ids(request),
		'seo_title': 'New Arrivals in Original Art | Ahmaan Art Gallery Pakistan',
		'seo_description': 'Discover the latest original paintings and contemporary artworks added to Ahmaan Art Gallery, with delivery across Pakistan.',
	})


@rate_limit(8, period=60)
def artwork_detail(request, slug):
	artwork = Artwork.objects.select_related('artist', 'category').prefetch_related('images', 'collections').filter(slug=slug).first()
	if not artwork:
		from gallery.views import artwork_detail as legacy_artwork_detail
		return legacy_artwork_detail(request, slug)

	recent_ids = [item for item in request.session.get('catalog_recently_viewed', []) if item != artwork.pk]
	request.session['catalog_recently_viewed'] = [artwork.pk, *recent_ids[:4]]
	related_query = Q(artist=artwork.artist) | Q(medium__iexact=artwork.medium)
	for style in artwork.style_tags:
		related_query |= Q(style_tags__icontains=style)
	for subject in artwork.subject_tags:
		related_query |= Q(subject_tags__icontains=subject)
	is_accessory = artwork.category.group == Category.Group.ACCESSORIES
	if is_accessory:
		related_query &= Q(category__group=Category.Group.ACCESSORIES)
	related = Artwork.objects.filter(related_query).exclude(pk=artwork.pk).distinct().select_related('artist', 'category').prefetch_related('images')[:4]
	recently_viewed = Artwork.objects.filter(pk__in=recent_ids[:4]).select_related('artist', 'category').prefetch_related('images')
	if request.GET.get('quick') == '1':
		return render(request, 'gallery/partials/_quick_view.html', {'artwork': artwork})

	notify_form = NotifyRequestForm()
	review_form = ReviewForm()
	if request.method == 'POST' and request.POST.get('action') == 'notify':
		notify_form = NotifyRequestForm(request.POST)
		if notify_form.is_valid():
			notify = notify_form.save(commit=False)
			notify.artwork = artwork
			notify.save()
			messages.success(request, 'Your notification request has been saved.')
			return redirect(f'/artwork/{artwork.slug}/#notify-form')
	elif request.method == 'POST' and request.POST.get('action') == 'review':
		review_form = ReviewForm(request.POST, request.FILES)
		if review_form.is_valid():
			review = review_form.save(commit=False)
			review.artwork = artwork
			review.is_approved = False
			review.save()
			messages.success(request, 'Thank you. Your review has been sent for approval.')
			return redirect(f'/artwork/{artwork.slug}/#reviews')

	option_lists = {
		'size_options': SizeOption.objects.filter(is_active=True),
		'frame_options': FrameOption.objects.filter(is_active=True),
		'canvas_types': CanvasType.objects.filter(is_active=True),
	}
	base_url = settings.PUBLIC_SITE_URL.rstrip('/')
	product_url = f'{base_url}/artwork/{artwork.slug}/'
	images = [f'{base_url}{item.image.url}' for item in artwork.images.all() if item.image]
	if is_accessory:
		seo_title = f'{artwork.title} {artwork.category.name} | Ahmaan Art Gallery'
		seo_description = f'{artwork.title}, {artwork.category.name}. {artwork.medium}'
		if artwork.width and artwork.height:
			seo_description += f'. {artwork.width} × {artwork.height} cm'
	else:
		seo_title = artwork.meta_title or f'{artwork.title} Original {artwork.category.name} | Ahmaan Art Gallery'
		seo_description = artwork.meta_description or (
			f'Buy {artwork.medium} by {artwork.artist.name}. {artwork.mood_tagline} '
			f'{artwork.story[:140]} Shop original art in Pakistan.'
		)
	availability = 'https://schema.org/InStock' if artwork.status == Artwork.Status.AVAILABLE else 'https://schema.org/OutOfStock'
	return render(request, 'gallery/catalog_artwork_detail.html', {
		'artwork': artwork,
		'wishlist_ids': _wishlist_ids(request),
		'compare_ids': _compare_ids(request),
		'seo_title': seo_title,
		'seo_description': seo_description,
		'seo_image': images[0] if images else '',
		'product_jsonld': schema_json({
			'@context': 'https://schema.org',
			'@type': 'Product',
			'name': artwork.title,
			'description': seo_description,
			'category': artwork.category.name,
			'material': artwork.medium,
			'brand': {'@type': 'Brand', 'name': 'Ahmaan Art Gallery'},
			'url': product_url,
			**({'image': images} if images else {}),
			'offers': {
				'@type': 'Offer', 'url': product_url, 'priceCurrency': 'PKR',
				'price': str(artwork.base_price), 'availability': availability,
				'itemCondition': 'https://schema.org/NewCondition',
			},
		}),
		'breadcrumb_jsonld': schema_json({
			'@context': 'https://schema.org', '@type': 'BreadcrumbList',
			'itemListElement': [
				{'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': base_url + '/'},
				{'@type': 'ListItem', 'position': 2, 'name': 'Artworks', 'item': base_url + '/shop/'},
				{'@type': 'ListItem', 'position': 3, 'name': artwork.title, 'item': product_url},
			],
		}),
		'notify_form': notify_form,
		'review_form': review_form,
		'offer_form': ArtworkOfferForm(),
		'related_artworks': related,
		'recently_viewed': recently_viewed,
		'approved_reviews': artwork.reviews.filter(is_approved=True).select_related('artwork'),
		'average_rating': artwork.reviews.filter(is_approved=True).aggregate(value=Avg('rating'))['value'],
		'has_product_options': any(options.exists() for options in option_lists.values()),
		**option_lists,
	})


@require_POST
@rate_limit(5, period=3600)
def submit_offer(request, slug):
	artwork = get_object_or_404(Artwork, slug=slug, status=Artwork.Status.AVAILABLE)
	form = ArtworkOfferForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Please check the offer details and try again.')
		return redirect('gallery:artwork_detail', slug=artwork.slug)
	offer = form.save(commit=False)
	offer.artwork = artwork
	minimum_percent = SiteSettings.objects.values_list('minimum_offer_percent', flat=True).first() or 70
	minimum_price = (artwork.base_price * Decimal(minimum_percent) / Decimal(100)).quantize(Decimal('0.01'))
	if offer.offer_price < minimum_price:
		messages.error(request, f'Offers must be at least {minimum_percent}% of the asking price (PKR {minimum_price:,.0f}).')
		return redirect('gallery:artwork_detail', slug=artwork.slug)
	offer.save()
	admin_addresses = [email for _, email in getattr(settings, 'ADMINS', [])]
	if not admin_addresses:
		admin_addresses = [settings.ADMIN_EMAIL]
	send_mail(
		f'New offer for {artwork.title}',
		f'Name: {offer.name}\nPhone: {offer.phone}\nEmail: {offer.email}\nOffer: PKR {offer.offer_price:,.0f}\nMinimum: PKR {minimum_price:,.0f}',
		getattr(settings, 'DEFAULT_FROM_EMAIL', 'hello@ahmaanartgallery.pk'),
		admin_addresses,
		fail_silently=True,
	)
	messages.success(request, 'Your offer has been sent to the gallery. We will respond soon.')
	return redirect('gallery:artwork_detail', slug=artwork.slug)


@require_POST
def add_catalog_item(request, slug):
	artwork = get_object_or_404(Artwork, slug=slug, status=Artwork.Status.AVAILABLE)
	try:
		quantity = max(1, min(10, int(request.POST.get('quantity', '1'))))
	except (TypeError, ValueError):
		quantity = 1
	if artwork.is_one_of_a_kind or artwork.is_limited_edition:
		quantity = 1
	options = {}
	for form_key, model, session_key in (
		('size', SizeOption, 'size_id'), ('frame', FrameOption, 'frame_id'), ('canvas_type', CanvasType, 'canvas_type_id'),
	):
		value = request.POST.get(form_key, '')
		if value:
			option = model.objects.filter(pk=value, is_active=True).first()
			if not option:
				messages.error(request, 'Choose a valid customization option.')
				return redirect('gallery:artwork_detail', slug=artwork.slug)
			options[session_key] = option.pk
	line = {
		'id': uuid4().hex,
		'artwork_id': artwork.pk,
		'quantity': quantity,
		'custom_text': request.POST.get('custom_text', '').strip()[:1000],
		**options,
	}
	cart = request.session.get('catalog_cart', [])
	cart.append(line)
	request.session['catalog_cart'] = cart
	messages.success(request, f'{artwork.title} was added to your bag.')
	return redirect(f'/artwork/{artwork.slug}/#cart-panel')


@require_POST
def remove_catalog_item(request, line_id):
	cart = request.session.get('catalog_cart', [])
	request.session['catalog_cart'] = [item for item in cart if item.get('id') != line_id]
	next_url = request.POST.get('next', '')
	if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
		return redirect(next_url)
	return redirect('gallery:shop')


@require_POST
def update_catalog_item(request, line_id):
	cart = request.session.get('catalog_cart', [])
	line = next((item for item in cart if item.get('id') == line_id), None)
	if line:
		artwork = Artwork.objects.filter(pk=line.get('artwork_id')).first()
		try:
			quantity = int(request.POST.get('quantity', '1'))
		except (TypeError, ValueError):
			quantity = 1
		if quantity <= 0:
			cart.remove(line)
		elif not artwork or artwork.status != Artwork.Status.AVAILABLE:
			cart.remove(line)
			messages.error(request, 'That work is no longer available and was removed from your bag.')
		else:
			maximum = min(10, artwork.quantity)
			if artwork.is_one_of_a_kind:
				maximum = 1
			if artwork.is_limited_edition and artwork.remaining is not None:
				maximum = min(maximum, artwork.remaining)
			line['quantity'] = max(1, min(maximum, quantity))
	request.session['catalog_cart'] = cart
	next_url = request.POST.get('next', '')
	if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
		return redirect(next_url)
	return redirect('gallery:shop')


def artists_index(request):
	artists = Artist.objects.annotate(work_count=Count('artworks')).select_related('interview_article').order_by('name')
	for artist in artists:
		article = artist.interview_article
		if article and (not article.is_published or article.published_at > timezone.now()):
			artist.interview_article = None
	ads_enabled = settings.ADSENSE_ENABLED and bool(settings.ADSENSE_CLIENT_ID)
	base_url = settings.PUBLIC_SITE_URL.rstrip('/')
	return render(request, 'gallery/artists.html', {
		'artists': artists,
		'ad_slot': AdSlot.objects.filter(key='artist-list', is_active=True).first() if ads_enabled else None,
		'seo_title': 'Our Artists | Ahmaan Art Gallery Pakistan',
		'seo_description': 'Meet the artists whose original paintings and contemporary artworks are represented by Ahmaan Art Gallery in Pakistan.',
		'breadcrumb_jsonld': schema_json({
			'@context': 'https://schema.org', '@type': 'BreadcrumbList',
			'itemListElement': [
				{'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': f'{base_url}/'},
				{'@type': 'ListItem', 'position': 2, 'name': 'Our Artists', 'item': f'{base_url}/artists/'},
			],
		}),
	})


def artist_detail(request, slug):
	artist = get_object_or_404(Artist, slug=slug)
	artworks = artist.artworks.filter(status__in=(Artwork.Status.AVAILABLE, Artwork.Status.SOLD)).select_related('category').prefetch_related('images')
	interview = artist.interview_article
	if interview and (not interview.is_published or interview.published_at > timezone.now()):
		artist.interview_article = None
	base_url = settings.PUBLIC_SITE_URL.rstrip('/')
	artist_url = f'{base_url}/artists/{artist.slug}/'
	return render(request, 'gallery/artist_detail.html', {
		'artist': artist,
		'artworks': artworks,
		'breadcrumb_jsonld': schema_json({
			'@context': 'https://schema.org', '@type': 'BreadcrumbList',
			'itemListElement': [
				{'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': f'{base_url}/'},
				{'@type': 'ListItem', 'position': 2, 'name': 'Our Artists', 'item': f'{base_url}/artists/'},
				{'@type': 'ListItem', 'position': 3, 'name': artist.name, 'item': artist_url},
			],
		}),
		'artist_jsonld': schema_json({
			'@context': 'https://schema.org', '@type': 'Person', 'name': artist.name,
			'url': artist_url, 'description': artist.bio,
			**({'image': f'{base_url}{artist.photo.url}'} if artist.photo else {}),
			**({'address': {'@type': 'PostalAddress', 'addressLocality': artist.city, 'addressCountry': 'PK'}} if artist.city else {}),
		}),
		'seo_title': artist.meta_title or f'{artist.name} Original Art and Artist Profile | Ahmaan Art Gallery',
		'seo_description': artist.meta_description or artist.bio[:280] or f'Discover original paintings and artwork by {artist.name}, {artist.specialty}, at Ahmaan Art Gallery Pakistan.',
		'seo_image': f'{settings.PUBLIC_SITE_URL.rstrip("/")}{artist.photo.url}' if artist.photo else '',
	})


def archive(request):
	artworks = Artwork.objects.filter(status=Artwork.Status.SOLD).select_related('artist', 'category').prefetch_related('images')
	return render(request, 'gallery/archive.html', {'artworks': artworks})


def _wishlist_ids(request):
	if request.user.is_authenticated:
		guest_ids = request.session.pop('catalog_wishlist', [])
		if guest_ids:
			valid_ids = Artwork.objects.filter(pk__in=guest_ids).values_list('pk', flat=True)
			Wishlist.objects.bulk_create(
				[Wishlist(user=request.user, artwork_id=artwork_id) for artwork_id in valid_ids],
				ignore_conflicts=True,
			)
		return list(request.user.artwork_wishlist.values_list('artwork_id', flat=True))
	return [int(item) for item in request.session.get('catalog_wishlist', []) if str(item).isdigit()]


def _legacy_wishlist_ids(request):
	if request.user.is_authenticated:
		guest_ids = request.session.pop('legacy_wishlist', [])
		if guest_ids:
			valid_ids = LegacyArtwork.objects.filter(pk__in=guest_ids).values_list('pk', flat=True)
			LegacyWishlist.objects.bulk_create(
				[LegacyWishlist(user=request.user, artwork_id=artwork_id) for artwork_id in valid_ids],
				ignore_conflicts=True,
			)
		return list(request.user.legacy_artwork_wishlist.values_list('artwork_id', flat=True))
	return [int(item) for item in request.session.get('legacy_wishlist', []) if str(item).isdigit()]


def wishlist_page(request):
	ids = _wishlist_ids(request)
	artworks = Artwork.objects.filter(pk__in=ids).select_related('artist', 'category').prefetch_related('images')
	legacy_ids = _legacy_wishlist_ids(request)
	legacy_artworks = LegacyArtwork.objects.filter(pk__in=legacy_ids).select_related('category')
	return render(request, 'gallery/wishlist.html', {
		'artworks': artworks,
		'wishlist_ids': ids,
		'legacy_artworks': legacy_artworks,
		'legacy_wishlist_ids': legacy_ids,
		'wishlist_total_count': len(ids) + len(legacy_ids),
	})


@require_POST
def legacy_wishlist_toggle(request, artwork_id):
	artwork = get_object_or_404(LegacyArtwork, pk=artwork_id)
	ids = _legacy_wishlist_ids(request)
	if request.user.is_authenticated:
		item, created = LegacyWishlist.objects.get_or_create(user=request.user, artwork=artwork)
		if not created:
			item.delete()
			added = False
		else:
			added = True
		count = request.user.artwork_wishlist.count() + request.user.legacy_artwork_wishlist.count()
	else:
		if artwork.pk in ids:
			ids.remove(artwork.pk)
			added = False
		else:
			ids.append(artwork.pk)
			added = True
		request.session['legacy_wishlist'] = ids
		count = len(ids) + len(_wishlist_ids(request))
	data = {'added': added, 'count': count, 'artwork_id': artwork.pk, 'kind': 'legacy'}
	if request.headers.get('HX-Request') == 'true':
		return _htmx_event('wishlistUpdated', data)
	return JsonResponse(data)


@require_POST
def wishlist_toggle(request, artwork_id):
	artwork = get_object_or_404(Artwork, pk=artwork_id)
	ids = _wishlist_ids(request)
	if request.user.is_authenticated:
		item, created = Wishlist.objects.get_or_create(user=request.user, artwork=artwork)
		if not created:
			item.delete()
			added = False
		else:
			added = True
		count = request.user.artwork_wishlist.count() + request.user.legacy_artwork_wishlist.count()
	else:
		if artwork.pk in ids:
			ids.remove(artwork.pk)
			added = False
		else:
			ids.append(artwork.pk)
			added = True
		request.session['catalog_wishlist'] = ids
		count = len(ids) + len(_legacy_wishlist_ids(request))
	data = {'added': added, 'count': count, 'artwork_id': artwork.pk, 'kind': 'catalog'}
	if request.headers.get('HX-Request') == 'true':
		return _htmx_event('wishlistUpdated', data)
	return JsonResponse(data)


def _compare_ids(request):
	stored_ids = request.session.get('catalog_compare', [])
	valid_ids = list(Artwork.objects.filter(pk__in=stored_ids).values_list('pk', flat=True))
	ordered_ids = [artwork_id for artwork_id in stored_ids if artwork_id in valid_ids]
	request.session['catalog_compare'] = ordered_ids
	return ordered_ids


def _legacy_compare_ids(request):
	stored_ids = request.session.get('legacy_compare', [])
	valid_ids = list(LegacyArtwork.objects.filter(pk__in=stored_ids).values_list('pk', flat=True))
	ordered_ids = [artwork_id for artwork_id in stored_ids if artwork_id in valid_ids]
	request.session['legacy_compare'] = ordered_ids
	return ordered_ids


def _compare_event_ids(catalog_ids, legacy_ids):
	return [f'catalog:{artwork_id}' for artwork_id in catalog_ids] + [f'legacy:{artwork_id}' for artwork_id in legacy_ids]


def compare_page(request):
	ids = _compare_ids(request)
	artworks_by_id = Artwork.objects.filter(pk__in=ids).select_related('artist', 'category').in_bulk()
	artworks = [artworks_by_id[artwork_id] for artwork_id in ids if artwork_id in artworks_by_id]
	legacy_ids = _legacy_compare_ids(request)
	legacy_by_id = LegacyArtwork.objects.filter(pk__in=legacy_ids).select_related('category').in_bulk()
	legacy_artworks = [legacy_by_id[artwork_id] for artwork_id in legacy_ids if artwork_id in legacy_by_id]
	compare_items = [{
		'id': artwork.pk,
		'kind': 'catalog',
		'title': artwork.title,
		'artist': artwork.artist.name,
		'artist_url': f'/artists/{artwork.artist.slug}/',
		'width': artwork.width,
		'height': artwork.height,
		'medium': artwork.medium,
		'price': artwork.base_price,
		'url': f'/artwork/{artwork.slug}/',
	} for artwork in artworks]
	compare_items.extend({
		'id': artwork.pk,
		'kind': 'legacy',
		'title': artwork.title,
		'artist': artwork.artist,
		'artist_url': '',
		'dimensions': artwork.dimensions,
		'medium': artwork.medium,
		'price': artwork.price,
		'url': f'/artwork/{artwork.slug}/',
	} for artwork in legacy_artworks)
	for item in compare_items:
		item['toggle_url'] = f"/compare/{item['kind']}-toggle/{item['id']}/"
	return render(request, 'gallery/compare.html', {
		'artworks': artworks,
		'compare_ids': ids,
		'legacy_compare_ids': legacy_ids,
		'compare_items': compare_items,
		'wishlist_ids': _wishlist_ids(request),
		'legacy_wishlist_ids': _legacy_wishlist_ids(request),
	})


@require_POST
def compare_toggle(request, artwork_id):
	artwork = get_object_or_404(Artwork, pk=artwork_id)
	ids = _compare_ids(request)
	legacy_ids = _legacy_compare_ids(request)
	full = False
	if artwork.pk in ids:
		ids.remove(artwork.pk)
		added = False
	elif len(ids) + len(legacy_ids) >= 3:
		added = False
		full = True
	else:
		ids.append(artwork.pk)
		added = True
	request.session['catalog_compare'] = ids
	data = {
		'added': added,
		'count': len(ids) + len(legacy_ids),
		'ids': _compare_event_ids(ids, legacy_ids),
		'artwork_id': artwork.pk,
		'artwork_type': 'catalog',
		'full': full,
	}
	if request.headers.get('HX-Request') == 'true':
		return _htmx_event('compareUpdated', data)
	if full:
		messages.info(request, 'Compare up to three artworks at a time.')
	return redirect('gallery:compare')


@require_POST
def legacy_compare_toggle(request, artwork_id):
	artwork = get_object_or_404(LegacyArtwork, pk=artwork_id)
	ids = _compare_ids(request)
	legacy_ids = _legacy_compare_ids(request)
	full = False
	if artwork.pk in legacy_ids:
		legacy_ids.remove(artwork.pk)
		added = False
	elif len(ids) + len(legacy_ids) >= 3:
		added = False
		full = True
	else:
		legacy_ids.append(artwork.pk)
		added = True
	request.session['legacy_compare'] = legacy_ids
	data = {
		'added': added,
		'count': len(ids) + len(legacy_ids),
		'ids': _compare_event_ids(ids, legacy_ids),
		'artwork_id': artwork.pk,
		'artwork_type': 'legacy',
		'full': full,
	}
	if request.headers.get('HX-Request') == 'true':
		return _htmx_event('compareUpdated', data)
	if full:
		messages.info(request, 'Compare up to three artworks at a time.')
	return redirect('gallery:compare')


def bundle_detail(request, slug):
	bundle = get_object_or_404(ArtworkBundle.objects.filter(is_active=True).prefetch_related('bundle_items__artwork__images', 'bundle_items__artwork__artist'), slug=slug)
	return render(request, 'gallery/bundle_detail.html', {'bundle': bundle})


def search(request):
	query = request.GET.get('q', '').strip()
	if len(query) < 2:
		if request.headers.get('HX-Request') == 'true':
			return render(request, 'gallery/partials/_search_results.html', {'query': query, 'results': []})
		return JsonResponse({'results': []})
	legacy = LegacyArtwork.objects.filter(is_available=True).filter(Q(title__icontains=query) | Q(artist__icontains=query) | Q(category__name__icontains=query)).select_related('category')[:5]
	catalog = Artwork.objects.filter(Q(title__icontains=query) | Q(artist__name__icontains=query) | Q(category__name__icontains=query)).select_related('artist', 'category').prefetch_related('images')[:5]
	artists = Artist.objects.filter(Q(name__icontains=query) | Q(specialty__icontains=query))[:3]
	collections = Collection.objects.filter(Q(name__icontains=query) | Q(short_description__icontains=query))[:3]
	results = []
	for artwork in legacy:
		results.append({'title': artwork.title, 'artist': artwork.artist, 'category': artwork.category.name, 'url': f'/artwork/{artwork.slug}/', 'price': f'PKR {artwork.price:,.0f}' if artwork.price is not None else 'Price on request', 'type': 'Artwork', 'thumbnail': artwork.image_url})
	for artwork in catalog:
		image = artwork.images.first()
		results.append({'title': artwork.title, 'artist': artwork.artist.name, 'category': artwork.category.name, 'url': f'/artwork/{artwork.slug}/', 'price': f'PKR {artwork.base_price:,.0f}', 'type': 'Artwork', 'thumbnail': image.image.url if image else ''})
	for artist in artists:
		results.append({'title': artist.name, 'artist': artist.specialty or 'Artist', 'category': 'Artist profile', 'url': f'/artists/{artist.slug}/', 'price': '', 'type': 'Artist', 'thumbnail': artist.photo.url if artist.photo else ''})
	for collection in collections:
		results.append({'title': collection.name, 'artist': collection.short_description, 'category': 'Collection', 'url': f'/collections/{collection.slug}/', 'price': '', 'type': 'Collection', 'thumbnail': collection.cover_image.url if collection.cover_image else ''})
	results = results[:12]
	if request.headers.get('HX-Request') == 'true':
		return render(request, 'gallery/partials/_search_results.html', {'query': query, 'results': results})
	return JsonResponse({'results': results})
