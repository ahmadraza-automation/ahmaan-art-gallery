from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from uuid import uuid4

from catalog.models import Artwork as CatalogArtwork
from orders.models import Coupon

from core.forms import ConsultationRequestForm, DesignerInquiryForm
from core.models import (
	AdSlot, ArtMatchQuestion, CityDeliveryTime, CuratorAdviceBanner, FAQ,
	JournalPost, NewsletterSubscriber, ShippingPaymentContent, SiteSettings,
)
from core.seo import schema_json
from core.security import rate_limit


def journal_index(request):
	posts = JournalPost.objects.filter(is_published=True, published_at__lte=timezone.now()).order_by('-published_at')
	category = request.GET.get('category', '')
	if category in JournalPost.Category.values:
		posts = posts.filter(category=category)
	page_obj = Paginator(posts, 9).get_page(request.GET.get('page'))
	ads_enabled = settings.ADSENSE_ENABLED and bool(settings.ADSENSE_CLIENT_ID)
	return render(request, 'gallery/journal.html', {
		'page_obj': page_obj,
		'posts': page_obj.object_list,
		'active_category': category,
		'categories': JournalPost.Category.choices,
		'ad_slot': AdSlot.objects.filter(key='journal-list', is_active=True).first() if ads_enabled else None,
		'breadcrumb_jsonld': _breadcrumb_schema((('Home', '/'), ('Journal', '/journal/'))),
		'seo_title': 'Art Journal: Artist Stories and Collecting Guides | Ahmaan Art Gallery',
		'seo_description': 'Read artist stories, studio notes, and practical guides to collecting original paintings and contemporary art in Pakistan.',
	})


def journal_detail(request, slug):
	post = get_object_or_404(JournalPost, slug=slug, is_published=True, published_at__lte=timezone.now())
	related_posts = JournalPost.objects.filter(is_published=True, published_at__lte=timezone.now()).exclude(pk=post.pk).filter(category=post.category)[:3]
	base_url = settings.PUBLIC_SITE_URL.rstrip('/')
	post_url = f'{base_url}/journal/{post.slug}/'
	image_url = f'{base_url}{post.cover_image.url}' if post.cover_image else ''
	seo_description = post.meta_description or post.excerpt
	ads_enabled = settings.ADSENSE_ENABLED and bool(settings.ADSENSE_CLIENT_ID)
	return render(request, 'gallery/journal_detail.html', {
		'post': post,
		'related_posts': related_posts,
		'ad_slot': AdSlot.objects.filter(key='journal-post', is_active=True).first() if ads_enabled else None,
		'seo_title': post.meta_title or f'{post.title} | Ahmaan Art Gallery Journal',
		'seo_description': seo_description,
		'seo_image': image_url,
		'article_jsonld': schema_json({
			'@context': 'https://schema.org', '@type': 'BlogPosting',
			'headline': post.title, 'description': seo_description,
			'datePublished': post.published_at.isoformat(),
			'articleSection': post.get_category_display(),
			'author': {'@type': 'Person', 'name': post.author},
			'publisher': {'@type': 'Organization', 'name': 'Ahmaan Art Gallery'},
			'url': post_url, **({'image': image_url} if image_url else {}),
		}),
		'breadcrumb_jsonld': _breadcrumb_schema((('Home', '/'), ('Journal', '/journal/'), (post.title, post_url))),
	})


def _breadcrumb_schema(items):
	base_url = settings.PUBLIC_SITE_URL.rstrip('/')
	return schema_json({
		'@context': 'https://schema.org', '@type': 'BreadcrumbList',
		'itemListElement': [
			{'@type': 'ListItem', 'position': index, 'name': label, 'item': url if url.startswith('http') else f'{base_url}{url}'}
			for index, (label, url) in enumerate(items, start=1)
		],
	})


def support_page(request, page_name, title, intro, body=''):
	site_settings = SiteSettings.objects.first()
	policy_fields = {
		'shipping': 'shipping_policy',
		'returns': 'returns_policy',
		'privacy': 'privacy_policy',
		'terms': 'terms_conditions',
	}
	policy_field = policy_fields.get(page_name)
	if site_settings and policy_field and getattr(site_settings, policy_field):
		body = getattr(site_settings, policy_field)
	if page_name == 'faq' and site_settings and site_settings.faq_intro:
		intro = site_settings.faq_intro
	context = {
		'page_title': title,
		'intro': intro,
		'site_settings': site_settings,
		'seo_title': f'{title} | Ahmaan Art Gallery Pakistan',
		'seo_description': intro,
		'breadcrumb_jsonld': _breadcrumb_schema((('Home', '/'), (title, request.path))),
	}
	if page_name == 'returns' and site_settings:
		context['extra_policy_sections'] = [
			{'title': heading, 'text': getattr(site_settings, field_name)}
			for field_name, heading in (
				('cancellation_policy', 'Cancellations'),
				('damage_in_transit_policy', 'Damage in transit'),
				('authenticity_policy', 'Authenticity'),
			)
			if getattr(site_settings, field_name)
		]
	if page_name == 'faq':
		items = list(FAQ.objects.filter(is_published=True).order_by('category', 'order', 'pk'))
		context.update({
			'faq_items': items,
			'faq_jsonld': schema_json({
				'@context': 'https://schema.org',
				'@type': 'FAQPage',
				'mainEntity': [{
					'@type': 'Question',
					'name': item.question,
					'acceptedAnswer': {'@type': 'Answer', 'text': item.answer},
				} for item in items],
			}),
		})
		return render(request, 'gallery/faq.html', context)
	else:
		context['body'] = body
	return render(request, 'gallery/content_page.html', context)


def faq_page(request):
	return support_page(request, 'faq', 'Frequently asked questions', 'Helpful notes on collecting, delivery, commissions, and caring for your artwork.')


def shipping_page(request):
	return support_page(
		request,
		'shipping',
		'Shipping',
		'We package every work with care and ship across Pakistan using trusted local partners.',
		'Every piece is wrapped, insured where needed, and photographed before it leaves the studio. Delivery times vary with location and framing, but we aim to keep updates clear and timely throughout the process.',
	)


def returns_page(request):
	return support_page(
		request,
		'returns',
		'Returns and exchanges',
		'We want your piece to feel right in your space, and we are happy to help if something is not quite right.',
		'If a work arrives damaged or significantly differs from the description, please contact the gallery within 48 hours with photos so we can resolve it together. For collector-led changes of mind, we review each request individually and may offer a return or exchange depending on the item and condition.',
	)


def privacy_page(request):
	return support_page(
		request,
		'privacy',
		'Privacy Policy',
		'Your information is used only to support your order, make communication easier, and improve the gallery experience.',
		'We keep customer contact details private and do not sell personal data. Information is used for orders, delivery communication, and optional studio notes. If advertising is enabled, Google AdSense may process browser or device information to serve ads only after you accept optional cookies. Read our Cookie Policy for consent details. Contact the gallery to update your information or stop receiving emails.',
	)


def terms_page(request):
	return support_page(
		request,
		'terms',
		'Terms and conditions',
		'By purchasing from Ahmaan Art Gallery, you agree to these simple terms for order, delivery, and care.',
		'Artwork is sold as described, subject to availability and careful packaging. We do our best to represent every piece accurately, but final appearance can vary slightly with screen calibration or lighting. Orders are confirmed once the gallery acknowledges them; payment and delivery details remain subject to our standard process and any accepted custom commission arrangements.',
	)


@rate_limit(5, period=3600)
def for_designers(request):
	form = DesignerInquiryForm(request.POST or None)
	if request.method == 'POST' and form.is_valid() and not form.cleaned_data.get('website'):
		form.save()
		messages.success(request, 'Thank you. The gallery team will be in touch about your project.')
		return redirect('core:for_designers')
	return render(request, 'gallery/for_designers.html', {
		'form': form,
		'seo_title': 'Art for Interior Designers | Ahmaan Art Gallery Pakistan',
		'seo_description': 'Work with Ahmaan Art Gallery to source original art for residential, hospitality, and commercial interiors across Pakistan.',
		'breadcrumb_jsonld': _breadcrumb_schema((('Home', '/'), ('For Interior Designers', '/for-designers/'))),
	})


def shipping_payments(request):
	content = ShippingPaymentContent.objects.first() or ShippingPaymentContent()
	cities = CityDeliveryTime.objects.filter(is_active=True)
	site_settings = SiteSettings.objects.first()
	return render(request, 'gallery/shipping_payments.html', {
		'content': content,
		'cities': cities,
		'site_settings': site_settings,
		'seo_title': 'Shipping & Payments Across Pakistan | Ahmaan Art Gallery',
		'seo_description': 'Read about artwork delivery across Pakistan, cash on delivery, bank transfer, JazzCash, Easypaisa, and city delivery estimates.',
		'breadcrumb_jsonld': _breadcrumb_schema((('Home', '/'), ('Shipping & Payments', '/shipping-payments/'))),
	})


def cookie_policy(request):
	site_settings = SiteSettings.objects.first()
	body = 'Essential cookies support core functions such as the shopping bag, account sessions, and security. Optional advertising cookies may be used to display relevant advertising only after consent. Use Cookie settings in the site footer to change your choice; the preference is stored in this browser.'
	if site_settings and site_settings.cookie_policy:
		body = site_settings.cookie_policy
	return render(request, 'gallery/content_page.html', {
		'page_title': 'Cookie Policy',
		'intro': 'We use essential cookies to keep the gallery working and optional cookies only with your consent.',
		'body': body,
		'site_settings': site_settings,
		'seo_title': 'Cookie Policy | Ahmaan Art Gallery Pakistan',
		'seo_description': 'Learn how Ahmaan Art Gallery uses essential and optional cookies and how to manage your consent.',
		'breadcrumb_jsonld': _breadcrumb_schema((('Home', '/'), ('Cookie Policy', '/cookie-policy/'))),
	})


def art_match(request):
	questions = ArtMatchQuestion.objects.filter(is_active=True).prefetch_related('options').order_by('order', 'pk')
	banner = CuratorAdviceBanner.objects.filter(is_active=True).first()
	site_settings = SiteSettings.objects.first()
	selected_answers = {}
	answer_labels = {}
	matching_artworks = []
	question_map = {question.key: question for question in questions}
	quiz_submitted = request.method == 'POST' and request.POST.get('action') == 'quiz'
	if quiz_submitted:
		for question in questions:
			value = request.POST.get(f'question_{question.pk}')
			if value:
				option = question.options.filter(value=value).first()
				if option:
					selected_answers[question.key] = option.value
					answer_labels[question.key] = option.label
		if len(selected_answers) == len(questions) and questions:
			matching_artworks = _matching_artworks(selected_answers, question_map)
		else:
			messages.error(request, 'Please answer every quiz question to see your artwork matches.')
	consultation_submitted = request.method == 'POST' and request.POST.get('action') != 'quiz'
	form = ConsultationRequestForm(request.POST if consultation_submitted else None)
	if consultation_submitted and form.is_valid() and not form.cleaned_data.get('website'):
		form.save()
		messages.success(request, 'Thanks for reaching out. Our curator will get back to you soon.')
		return redirect('core:art_match')
	if consultation_submitted and not form.is_valid():
		messages.error(request, 'Please check the details and try again.')
	recommended_summary = 'We can help you narrow the selection to a few thoughtful options based on your room, style, and budget.'
	if selected_answers:
		recommended_summary = 'Based on your answers, we can guide you toward pieces that fit your room, palette, and budget with a more personal edit.'
	for question in questions:
		question.selected_value = selected_answers.get(question.key, '')
	answer_rows = [{'key': key.title(), 'label': answer_labels.get(key, value)} for key, value in selected_answers.items()]
	return render(request, 'gallery/art_match.html', {
		'questions': questions,
		'banner': banner,
		'form': form,
		'site_settings': site_settings,
		'selected_answers': selected_answers,
		'answer_labels': answer_labels,
		'answer_rows': answer_rows,
		'matching_artworks': matching_artworks,
		'quiz_submitted': quiz_submitted,
		'recommended_summary': recommended_summary,
		'seo_title': 'Art Match | Ahmaan Art Gallery Pakistan',
		'seo_description': 'Share a few notes about your room and budget and get curated art recommendations from Ahmaan Art Gallery.',
	})


def _matching_artworks(selected_answers, question_map):
	if not selected_answers:
		return []
	artworks = list(CatalogArtwork.objects.filter(status=CatalogArtwork.Status.AVAILABLE).select_related('artist', 'category').prefetch_related('rooms', 'images').order_by('-is_featured', '-created_at')[:24])
	results = []
	for artwork in artworks:
		matches = True
		if 'room' in selected_answers:
			room_value = selected_answers['room'].lower()
			if not any(room.slug == room_value or room.name.lower() == room_value for room in artwork.rooms.all()):
				matches = False
		if matches and 'style' in selected_answers:
			style_value = selected_answers['style'].lower()
			if not any(tag.lower() == style_value for tag in artwork.style_tags or []):
				matches = False
		if matches and 'color' in selected_answers:
			color_value = selected_answers['color'].lower()
			if not any(tag.lower() == color_value for tag in artwork.color_palette_tags or []):
				matches = False
		if matches and 'budget' in selected_answers:
			budget_question = question_map.get('budget')
			option = budget_question.options.filter(value=selected_answers['budget']).first() if budget_question else None
			if option:
				if option.minimum_price is not None and artwork.base_price < option.minimum_price:
					matches = False
				if option.maximum_price is not None and artwork.base_price > option.maximum_price:
					matches = False
		if matches and 'size' in selected_answers:
			size_value = selected_answers['size'].lower()
			size_dimension = (artwork.width or 0) * (artwork.height or 0)
			size_map = {'small': size_dimension <= 2500, 'medium': 2500 < size_dimension <= 7000, 'large': 7000 < size_dimension <= 16000, 'oversized': size_dimension > 16000}
			if size_value not in size_map or not size_map[size_value]:
				matches = False
		if matches:
			results.append(artwork)
		if len(results) >= 4:
			break
	return results


def robots_txt(request):
	site_url = settings.PUBLIC_SITE_URL.rstrip('/')
	return HttpResponse(
		f'User-agent: *\nAllow: /\nDisallow: /account/\nDisallow: /checkout/\nDisallow: /{settings.DJANGO_ADMIN_URL}\nSitemap: {site_url}/sitemap.xml\n',
		content_type='text/plain; charset=utf-8',
	)


def ads_txt(request):
	client_id = settings.ADSENSE_CLIENT_ID
	if not settings.ADSENSE_ENABLED or not client_id:
		return HttpResponse('', content_type='text/plain; charset=utf-8')
	publisher_id = client_id.removeprefix('ca-')
	return HttpResponse(f'google.com, {publisher_id}, DIRECT, f08c47fec0942fa0\n', content_type='text/plain; charset=utf-8')


@require_POST
@rate_limit(8, period=60)
def newsletter_signup(request):
	email = request.POST.get('email', '').strip().lower()
	if request.POST.get('website'):
		return _safe_return(request, request.POST.get('next', '/'))
	try:
		validate_email(email)
	except ValidationError:
		messages.error(request, 'Enter a valid email address to join the list.')
	else:
		NewsletterSubscriber.objects.update_or_create(email=email, defaults={'is_active': True})
		if request.POST.get('discount_popup'):
			code = _create_discount_coupon_for_email(email)
			messages.success(request, f'You are on the list. Your 10% welcome code is {code}.')
		else:
			messages.success(request, 'You are on the list. Look out for a note from the gallery.')
	return _safe_return(request, request.POST.get('next', '/'))


def _create_discount_coupon_for_email(email):
	existing_coupon = Coupon.objects.filter(issued_to_email=email).first()
	if existing_coupon:
		return existing_coupon.code
	while True:
		code = f'AHMAAN10-{uuid4().hex[:8].upper()}'
		if not Coupon.objects.filter(code=code).exists():
			Coupon.objects.create(code=code, issued_to_email=email, discount_percent=10, minimum_order=0, usage_limit=1, is_active=True)
			return code


def _safe_return(request, target):
	if url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
		return redirect(target)
	return redirect('/')