from decimal import Decimal

from django.conf import settings
from core.seo import schema_json
from catalog.models import (
	Artwork as CatalogArtwork, CanvasType, Collection, FrameOption, SizeOption,
	Wishlist,
)
from core.models import Banner, SiteSettings
from .models import Artwork, Order
from .pricing import artwork_price


def storefront(request):
	site_settings = SiteSettings.objects.first()
	announcements = []
	announcement_bar_enabled = site_settings.announcement_bar_enabled if site_settings else True
	if announcement_bar_enabled:
		announcements.append(
			site_settings.announcement_bar_text if site_settings and site_settings.announcement_bar_text
			else 'Free shipping / Worldwide delivery / WhatsApp par rabta karein'
		)
		if site_settings and site_settings.free_shipping_threshold:
			announcements.append(f'Complimentary delivery on orders above PKR {site_settings.free_shipping_threshold:,.0f}')
		announcements.append('Custom commissions are open for considered, made-to-order work.')
	configured_whatsapp = site_settings.whatsapp_number if site_settings and site_settings.whatsapp_number else settings.WHATSAPP_NUMBER
	whatsapp_number = ''.join(character for character in configured_whatsapp if character.isdigit())
	cart = request.session.get('gallery_cart', [])
	artwork_ids = {item.get('artwork_id') for item in cart if isinstance(item, dict) and item.get('artwork_id')}
	artworks = Artwork.objects.filter(pk__in=artwork_ids, is_available=True).select_related('category')
	artworks_by_id = {artwork.pk: artwork for artwork in artworks}
	lines = []
	total = Decimal('0.00')
	count = 0
	for item in cart:
		if not isinstance(item, dict):
			continue
		artwork = artworks_by_id.get(item.get('artwork_id'))
		if not artwork:
			continue
		quantity = max(1, min(20, int(item.get('quantity', 1))))
		price = artwork_price(artwork, item.get('size', 'medium'))
		line_total = price * quantity if price is not None else None
		if line_total is not None:
			total += line_total
		lines.append({
			**item,
			'artwork': artwork,
			'quantity': quantity,
			'unit_price': price,
			'line_total': line_total,
			'size_label': Order.Size(item.get('size', 'medium')).label,
			'frame_label': Order.Frame(item.get('frame', 'none')).label,
		})
		count += quantity
	catalog_cart_lines = []
	catalog_cart_total = Decimal('0.00')
	catalog_cart = request.session.get('catalog_cart', [])
	catalog_ids = {item.get('artwork_id') for item in catalog_cart if isinstance(item, dict)}
	catalog_artworks = CatalogArtwork.objects.filter(pk__in=catalog_ids).select_related('artist')
	catalog_by_id = {artwork.pk: artwork for artwork in catalog_artworks}
	for item in catalog_cart:
		if not isinstance(item, dict):
			continue
		artwork = catalog_by_id.get(item.get('artwork_id'))
		if not artwork:
			continue
		quantity = max(1, min(10, int(item.get('quantity', 1))))
		size = SizeOption.objects.filter(pk=item.get('size_id')).first() if item.get('size_id') else None
		frame = FrameOption.objects.filter(pk=item.get('frame_id')).first() if item.get('frame_id') else None
		canvas = CanvasType.objects.filter(pk=item.get('canvas_type_id')).first() if item.get('canvas_type_id') else None
		unit_price = artwork.base_price + sum((option.price_modifier for option in (size, frame, canvas) if option), start=Decimal('0.00'))
		line_total = unit_price * quantity
		catalog_cart_total += line_total
		catalog_cart_lines.append({'id': item.get('id', ''), 'artwork': artwork, 'quantity': quantity, 'size': size, 'frame': frame, 'canvas': canvas, 'custom_text': item.get('custom_text', ''), 'unit_price': unit_price, 'line_total': line_total})
		count += quantity
	wishlist_ids = list(request.user.artwork_wishlist.values_list('artwork_id', flat=True)) if request.user.is_authenticated else [int(item) for item in request.session.get('catalog_wishlist', []) if str(item).isdigit()]
	legacy_wishlist_ids = list(request.user.legacy_artwork_wishlist.values_list('artwork_id', flat=True)) if request.user.is_authenticated else [int(item) for item in request.session.get('legacy_wishlist', []) if str(item).isdigit()]
	compare_ids = [int(item) for item in request.session.get('catalog_compare', []) if str(item).isdigit()]
	legacy_compare_ids = [int(item) for item in request.session.get('legacy_compare', []) if str(item).isdigit()]
	free_shipping_threshold = site_settings.free_shipping_threshold if site_settings else Decimal('0.00')
	free_shipping_remaining = max(Decimal('0.00'), free_shipping_threshold - total - catalog_cart_total)
	shipping_progress = min(100, int((total + catalog_cart_total) * 100 / free_shipping_threshold)) if free_shipping_threshold else 100
	cart_suggestions = []
	if catalog_ids:
		category_ids = set(CatalogArtwork.objects.filter(pk__in=catalog_ids).values_list('category_id', flat=True))
		cart_suggestions = list(CatalogArtwork.objects.filter(
			status=CatalogArtwork.Status.AVAILABLE,
			category_id__in=category_ids,
		).exclude(pk__in=catalog_ids).select_related('artist').order_by('-is_featured', '-created_at')[:3])
	frame_upgrade = FrameOption.objects.filter(is_active=True, price_modifier__gt=0).order_by('price_modifier').first()
	page_seo = {
		'/': ('Original Pakistani Art and Paintings | Ahmaan Art Gallery', 'Discover original paintings, calligraphy, and contemporary art by Pakistani artists, selected for thoughtful homes and collectors.'),
		'/shop/': ('Original Paintings and Contemporary Art for Sale in Pakistan | Ahmaan Art Gallery', 'Shop original paintings, calligraphy, and contemporary art by Pakistani artists with secure delivery across Pakistan.'),
		'/collections/': ('Curated Original Art Collections | Ahmaan Art Gallery Pakistan', 'Explore curated collections of original paintings and contemporary art for homes, offices, and collectors in Pakistan.'),
		'/about/': ('About Ahmaan Art Gallery | Original Art from Pakistan', 'Meet Ahmaan Art Gallery, an independent Lahore gallery connecting collectors with original paintings and contemporary Pakistani art.'),
		'/contact/': ('Contact Ahmaan Art Gallery | Lahore Art Gallery Enquiries', 'Contact Ahmaan Art Gallery in Lahore about original artwork, custom commissions, delivery, or arranging a viewing.'),
		'/commission/': ('Custom Art Commissions and Portraits in Pakistan | Ahmaan Art Gallery', 'Request a custom portrait or original artwork commission. Share your idea, preferred size, and reference image with our Lahore gallery.'),
		'/archive/': ('Sold Original Artworks Archive | Ahmaan Art Gallery', 'Browse previously collected original paintings and contemporary artworks from Ahmaan Art Gallery Pakistan.'),
		'/wishlist/': ('Saved Original Artworks | Ahmaan Art Gallery', 'Review the original paintings and contemporary artworks you have saved from Ahmaan Art Gallery.'),
		'/checkout/': ('Secure Artwork Checkout and Delivery | Ahmaan Art Gallery', 'Complete your artwork order with delivery details and secure payment options available across Pakistan.'),
		'/account/': ('Collector Account and Artwork Orders | Ahmaan Art Gallery', 'Manage your Ahmaan Art Gallery collector profile and review your artwork orders.'),
		'/accounts/login/': ('Collector Sign In | Ahmaan Art Gallery Pakistan', 'Sign in to your Ahmaan Art Gallery account to manage saved details and follow your art orders.'),
		'/accounts/signup/': ('Create a Collector Account | Ahmaan Art Gallery Pakistan', 'Create an Ahmaan Art Gallery account to save original artworks and manage your collector details.'),
	}
	route_label = ' '.join(segment.replace('-', ' ') for segment in request.path.strip('/').split('/') if segment) or 'Original art gallery'
	default_seo_title, default_seo_description = page_seo.get(
		request.path,
		(
			f"{route_label.title()[-38:]} | Original Art in Pakistan | Ahmaan Art Gallery",
			f"Explore {route_label} at Ahmaan Art Gallery, featuring original paintings and contemporary art by Pakistani artists.",
		),
	)
	seo_noindex = request.path.startswith(('/account/', '/accounts/', '/checkout/', '/orders/', '/order/'))
	return {
		'cart_lines': lines,
		'catalog_cart_lines': catalog_cart_lines,
		'cart_count': count,
		'cart_total': total + catalog_cart_total,
		'free_shipping_threshold': free_shipping_threshold,
		'free_shipping_remaining': free_shipping_remaining,
		'shipping_progress': shipping_progress,
		'cart_suggestions': cart_suggestions,
		'frame_upgrade': frame_upgrade,
		'cart_has_unpriced': any(line['line_total'] is None for line in lines),
		'wishlist_ids': wishlist_ids,
		'wishlist_count': len(wishlist_ids) + len(legacy_wishlist_ids),
		'legacy_wishlist_ids': legacy_wishlist_ids,
		'compare_ids': compare_ids,
		'legacy_compare_ids': legacy_compare_ids,
		'compare_count': len(compare_ids) + len(legacy_compare_ids),
		'has_product_options': SizeOption.objects.filter(is_active=True).exists() or FrameOption.objects.filter(is_active=True).exists() or CanvasType.objects.filter(is_active=True).exists(),
		'site_settings': site_settings,
		'nav_collections': Collection.objects.order_by('order', 'name')[:6],
		'nav_featured_artworks': CatalogArtwork.objects.filter(is_featured=True).select_related('artist')[:3],
		'nav_promo_banner': Banner.objects.filter(is_active=True).first(),
		'announcement_messages': announcements,
		'announcement_bar_enabled': announcement_bar_enabled,
		'whatsapp_number': whatsapp_number,
		'seo_canonical_url': f"{settings.PUBLIC_SITE_URL.rstrip('/')}{request.path}",
		'organization_jsonld': schema_json({
			'@context': 'https://schema.org',
			'@type': 'ArtGallery',
			'name': 'Ahmaan Art Gallery',
			'url': settings.PUBLIC_SITE_URL.rstrip('/') + '/',
			'address': {
				'@type': 'PostalAddress',
				**({'streetAddress': site_settings.address} if site_settings and site_settings.address else {}),
				'addressLocality': 'Lahore',
				'addressCountry': 'PK',
			},
			**({'telephone': '+' + whatsapp_number} if whatsapp_number else {}),
			'sameAs': [url for url in (
				site_settings.instagram_url if site_settings else '',
				site_settings.facebook_url if site_settings else '',
				site_settings.pinterest_url if site_settings else '',
			) if url],
		}),
		'seo_title': default_seo_title,
		'seo_description': default_seo_description,
		'seo_noindex': seo_noindex,
		'adsense_enabled': settings.ADSENSE_ENABLED and bool(settings.ADSENSE_CLIENT_ID),
		'adsense_client_id': settings.ADSENSE_CLIENT_ID,
	}