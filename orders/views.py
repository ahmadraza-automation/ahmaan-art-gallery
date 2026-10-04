from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import AccountProfile, SavedAddress
from catalog.models import Artwork, CanvasType, FrameOption, SizeOption
from core.models import SiteSettings
from core.security import rate_limit
from gallery.models import Artwork as LegacyArtwork
from gallery.pricing import artwork_price
from orders.certificates import generate_order_certificate
from orders.forms import CheckoutForm, GiftCardRequestForm, OrderTrackingForm
from orders.models import Coupon, GiftCard, GiftCardRedemption, Order, OrderItem, PaymentProof
from orders.payments import get_payment_provider
from orders.reservations import release_expired_reservations, reserve_unique_artwork


class CartUnavailable(Exception):
	pass


def _settings():
	return SiteSettings.objects.first() or SiteSettings()


def _provider_choices(site_settings):
	available = [Order.PaymentMethod.COD]
	if site_settings.bank_account_number or site_settings.bank_iban:
		available.append(Order.PaymentMethod.BANK_TRANSFER)
	if site_settings.jazzcash_number:
		available.append(Order.PaymentMethod.JAZZCASH)
	if site_settings.easypaisa_number:
		available.append(Order.PaymentMethod.EASYPAISA)
	providers = [get_payment_provider(method).instructions(site_settings) for method in available]
	return [(provider.method, provider.label) for provider in providers], providers


@rate_limit(5, period=3600)
def gift_cards(request):
	form = GiftCardRequestForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		gift_card = form.save()
		admin_addresses = [email for _, email in getattr(settings, 'ADMINS', [])]
		if not admin_addresses:
			admin_addresses = [settings.ADMIN_EMAIL]
		send_mail(
			'New gift card request',
			f'Gift card request: PKR {gift_card.amount:,.0f}\nRecipient: {gift_card.recipient_name}\nEmail: {gift_card.recipient_email}\nMessage: {gift_card.message}\nReference code: {gift_card.code}',
			getattr(settings, 'DEFAULT_FROM_EMAIL', 'hello@ahmaanartgallery.pk'), admin_addresses, fail_silently=True,
		)
		messages.success(request, 'Your gift card request is with the gallery. We will contact you to arrange payment and delivery.')
		return redirect('orders:gift_cards')
	return render(request, 'orders/gift_cards.html', {
		'form': form,
		'seo_title': 'Art Gift Cards in PKR | Ahmaan Art Gallery Pakistan',
		'seo_description': 'Request an Ahmaan Art Gallery gift card in fixed PKR denominations, made for someone who loves original art.',
	})


def _checkout_initial(request):
	if not request.user.is_authenticated:
		return {}
	profile = AccountProfile.objects.filter(user=request.user).first()
	address = request.user.saved_gallery_addresses.filter(is_default=True).first()
	return {
		'customer_name': address.recipient_name if address else request.user.get_full_name() or request.user.username,
		'customer_email': request.user.email,
		'customer_phone': address.phone if address else profile.phone if profile else '',
		'delivery_address': '\n'.join(filter(None, (address.address_line1, address.address_line2, address.postal_code))) if address else profile.address if profile else '',
		'city': address.city if address else profile.city if profile else '',
		'saved_address': str(address.pk) if address else '',
	}


def _cart_rows(request):
	rows = []
	catalog_cart = request.session.get('catalog_cart', [])
	catalog_ids = {item.get('artwork_id') for item in catalog_cart if isinstance(item, dict)}
	catalog_by_id = {artwork.pk: artwork for artwork in Artwork.objects.filter(pk__in=catalog_ids).select_related('artist', 'category')}
	for item in catalog_cart:
		if not isinstance(item, dict):
			continue
		artwork = catalog_by_id.get(item.get('artwork_id'))
		if not artwork or artwork.status != Artwork.Status.AVAILABLE:
			raise CartUnavailable('A catalog work in your bag is no longer available.')
		quantity = max(1, min(10, int(item.get('quantity', 1))))
		if artwork.is_one_of_a_kind or artwork.is_limited_edition:
			quantity = 1
		size = SizeOption.objects.filter(pk=item.get('size_id'), is_active=True).first() if item.get('size_id') else None
		frame = FrameOption.objects.filter(pk=item.get('frame_id'), is_active=True).first() if item.get('frame_id') else None
		canvas = CanvasType.objects.filter(pk=item.get('canvas_type_id'), is_active=True).first() if item.get('canvas_type_id') else None
		unit_price = artwork.base_price + sum((option.price_modifier for option in (size, frame, canvas) if option), start=Decimal('0.00'))
		rows.append({
			'catalog_artwork': artwork, 'legacy_artwork': None, 'title': artwork.title,
			'quantity': quantity, 'size': size, 'frame': frame, 'canvas': canvas,
			'custom_text': item.get('custom_text', '').strip(), 'unit_price': unit_price,
			'line_total': unit_price * quantity,
		})

	legacy_cart = request.session.get('gallery_cart', [])
	legacy_ids = {item.get('artwork_id') for item in legacy_cart if isinstance(item, dict)}
	legacy_by_id = {artwork.pk: artwork for artwork in LegacyArtwork.objects.filter(pk__in=legacy_ids).select_related('category')}
	for item in legacy_cart:
		if not isinstance(item, dict):
			continue
		artwork = legacy_by_id.get(item.get('artwork_id'))
		if not artwork or not artwork.is_available:
			raise CartUnavailable('A work in your bag is no longer available.')
		quantity = max(1, min(20, int(item.get('quantity', 1))))
		unit_price = artwork_price(artwork, item.get('size', 'medium'))
		if unit_price is None:
			raise CartUnavailable(f'{artwork.title} needs a confirmed price before checkout.')
		rows.append({
			'catalog_artwork': None, 'legacy_artwork': artwork, 'title': artwork.title,
			'quantity': quantity, 'size': item.get('size', 'medium'), 'frame': item.get('frame', 'none'),
			'canvas': None, 'custom_text': item.get('custom_additions', '').strip(),
			'unit_price': unit_price, 'line_total': unit_price * quantity,
		})
	return rows


def _totals(rows, site_settings, coupon=None, gift_card=None):
	subtotal = sum((line['line_total'] for line in rows), start=Decimal('0.00'))
	shipping = Decimal('0.00')
	if subtotal and (not site_settings.free_shipping_threshold or subtotal < site_settings.free_shipping_threshold):
		shipping = site_settings.flat_shipping_rate
	discount = Decimal('0.00')
	if coupon:
		if coupon.discount_percent:
			discount = (subtotal * Decimal(coupon.discount_percent) / Decimal(100)).quantize(Decimal('0.01'))
		else:
			discount = coupon.discount_amount
		discount = min(discount, subtotal)
	if gift_card and gift_card.is_active and not gift_card.is_redeemed:
		discount += min(gift_card.amount, max(Decimal('0.00'), subtotal + shipping - discount))
	return subtotal, shipping, discount, max(Decimal('0.00'), subtotal + shipping - discount)


@rate_limit(8, period=60)
def checkout(request):
	release_expired_reservations()
	site_settings = _settings()
	try:
		cart_rows = _cart_rows(request)
	except CartUnavailable as error:
		request.session['catalog_cart'] = []
		request.session['gallery_cart'] = []
		messages.error(request, str(error))
		return redirect('gallery:shop')
	if not cart_rows:
		messages.info(request, 'Your bag is empty.')
		return redirect('gallery:shop')
	payment_choices, payment_options = _provider_choices(site_settings)
	initial = _checkout_initial(request)
	form = CheckoutForm(request.POST or None, request.FILES or None, user=request.user, payment_choices=payment_choices, initial=initial)
	coupon = None
	gift_card = None
	coupon_error = ''
	if request.method == 'POST' and form.is_valid():
		coupon_code = form.cleaned_data['coupon_code']
		if coupon_code:
			coupon = Coupon.objects.select_for_update().filter(code=coupon_code).first()
			if not coupon or not coupon.is_valid_now:
				form.add_error('coupon_code', 'This discount code is invalid or expired.')
			elif sum((line['line_total'] for line in cart_rows), start=Decimal('0.00')) < coupon.minimum_order:
				form.add_error('coupon_code', 'Your bag does not meet this code’s minimum order.')
				coupon = None
		gift_card_code = form.cleaned_data.get('gift_card_code')
		if gift_card_code:
			gift_card = GiftCard.objects.filter(code=gift_card_code, is_active=True, is_redeemed=False).first()
			if not gift_card:
				form.add_error('gift_card_code', 'This gift card is invalid, inactive, or already redeemed.')
		if not form.errors:
			return _create_order(request, form, cart_rows, site_settings, coupon, gift_card)
	if request.method == 'POST' and form.cleaned_data.get('coupon_code') and form.errors:
		coupon_error = 'Please review the discount code and checkout details.'
	subtotal, shipping, discount, total = _totals(cart_rows, site_settings, coupon, gift_card)
	local_today = timezone.localdate()
	return render(request, 'orders/checkout.html', {
		'form': form, 'cart_rows': cart_rows, 'subtotal': subtotal, 'shipping': shipping,
		'discount': discount, 'total': total, 'coupon': coupon, 'gift_card': gift_card, 'coupon_error': coupon_error,
		'site_settings': site_settings, 'payment_options': payment_options,
		'seo_title': 'Secure Artwork Checkout and Delivery | Ahmaan Art Gallery',
		'seo_description': 'Complete your original artwork order with delivery details and secure payment options available across Pakistan.',
		'delivery_start': local_today + timedelta(days=site_settings.minimum_delivery_days),
		'delivery_end': local_today + timedelta(days=site_settings.maximum_delivery_days),
	})


def _create_order(request, form, rows, site_settings, coupon, gift_card=None):
	cleaned = form.cleaned_data
	address_text = cleaned['delivery_address'].strip()
	city = cleaned['city'].strip()
	phone = cleaned['customer_phone'].strip()
	name = cleaned['customer_name'].strip()
	saved_address = None
	if request.user.is_authenticated and cleaned.get('saved_address'):
		saved_address = SavedAddress.objects.filter(pk=cleaned['saved_address'], user=request.user).first()
		if saved_address:
			name = saved_address.recipient_name
			phone = saved_address.phone
			city = saved_address.city
			address_text = '\n'.join(filter(None, (saved_address.address_line1, saved_address.address_line2, saved_address.postal_code)))
	subtotal, shipping, discount, total = _totals(rows, site_settings, coupon, gift_card)
	method = cleaned['payment_method']
	payment_status = Order.PaymentStatus.PROOF_SUBMITTED if method != Order.PaymentMethod.COD else Order.PaymentStatus.UNPAID
	now = timezone.now()
	try:
		with transaction.atomic():
			if gift_card:
				gift_card = GiftCard.objects.select_for_update().filter(pk=gift_card.pk, is_active=True, is_redeemed=False).first()
				if not gift_card:
					raise CartUnavailable('This gift card has already been redeemed or is no longer active.')
			reserved = set()
			for line in rows:
				artwork = line['catalog_artwork']
				if artwork and artwork.is_one_of_a_kind and artwork.pk not in reserved:
					if not reserve_unique_artwork(artwork.pk, now=now):
						raise CartUnavailable(f'{artwork.title} was just reserved by another collector.')
					reserved.add(artwork.pk)
			order = Order.objects.create(
				user=request.user if request.user.is_authenticated else None,
				customer_name=name, customer_email=cleaned['customer_email'].strip(), customer_phone=phone,
				delivery_address=address_text, city=city, payment_method=method,
				payment_status=payment_status, coupon=coupon, subtotal=subtotal,
				shipping_amount=shipping, discount_amount=discount, total=total,
				customer_note=cleaned['customer_note'],
			)
			for line in rows:
				OrderItem.objects.create(
					order=order,
					artwork=line['catalog_artwork'],
					title_at_order=line['title'],
					unit_price=line['unit_price'],
					quantity=line['quantity'],
					chosen_size=line['size'] if line['catalog_artwork'] else None,
					chosen_frame=line['frame'] if line['catalog_artwork'] else None,
					chosen_canvas=line['canvas'],
					custom_text=line['custom_text'],
				)
			proof = cleaned.get('payment_proof')
			if proof:
				PaymentProof.objects.create(order=order, image=proof, amount=total)
			if coupon:
				coupon.uses += 1
				coupon.save(update_fields=['uses'])
			if gift_card:
				gift_card.is_redeemed = True
				gift_card.redeemed_at = timezone.now()
				gift_card.redeemed_by_order = order
				gift_card.save(update_fields=['is_redeemed', 'redeemed_at', 'redeemed_by_order'])
				coupon_discount = _totals(rows, site_settings, coupon)[2]
				amount_applied = min(gift_card.amount, max(Decimal('0.00'), subtotal + shipping - coupon_discount))
				GiftCardRedemption.objects.create(gift_card=gift_card, order=order, amount_applied=amount_applied)
			request.session['catalog_cart'] = []
			request.session['gallery_cart'] = []
			request.session['orders_last_reference'] = order.reference
			generate_order_certificate(order)
	except CartUnavailable as error:
		messages.error(request, str(error))
		return redirect('gallery:shop')
	items_text = '\n'.join(
		f"- {line['quantity']} × {line['title']}; {getattr(line['size'], 'name', line['size'])}; {getattr(line['frame'], 'name', line['frame'])}; {line['custom_text'] or 'no note'}; PKR {line['line_total']:,.0f}"
		for line in rows
	)
	message = '\n'.join((
		f'Hello Ahmaan Art Gallery, I would like to confirm order {order.reference}.', items_text,
		f'Name: {name}', f'Phone: {phone}', f'Address: {address_text}, {city}',
		f'Total: PKR {total:,.0f}',
	))
	phone_number = ''.join(character for character in ((site_settings.whatsapp_number or settings.WHATSAPP_NUMBER)) if character.isdigit())
	whatsapp_url = f'https://wa.me/{phone_number}?text={quote(message)}' if phone_number else f'https://wa.me/?text={quote(message)}'
	certificate_url = f'{settings.PUBLIC_SITE_URL.rstrip("/")}{reverse("orders:verify_certificate", args=[order.certificate_id])}'
	email_body = f"Thank you for your order {order.reference}.\n\n{items_text}\n\nSubtotal: PKR {subtotal:,.0f}\nShipping: PKR {shipping:,.0f}\nDiscount: PKR {discount:,.0f}\nTotal: PKR {total:,.0f}\n\nTrack your order at {settings.PUBLIC_SITE_URL.rstrip('/')}{reverse('orders:track')}\nYour certificate will be available at {certificate_url}"
	send_mail('Your Ahmaan Art Gallery order', email_body, settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'orders@ahmaanartgallery.pk', [order.customer_email], fail_silently=True)
	return redirect('orders:confirmation', reference=order.reference)


def confirmation(request, reference):
	order = get_object_or_404(Order.objects.prefetch_related('items__artwork__artist'), reference=reference)
	if not (request.user.is_authenticated and order.user_id == request.user.pk) and request.session.get('orders_last_reference') != order.reference:
		return redirect('gallery:home')
	items = list(order.items.select_related('artwork', 'chosen_size', 'chosen_frame', 'chosen_canvas'))
	phone_number = ''.join(character for character in (_settings().whatsapp_number or settings.WHATSAPP_NUMBER) if character.isdigit())
	message = f"Hello Ahmaan Art Gallery, I'd like to confirm order {order.reference}."
	whatsapp_url = f'https://wa.me/{phone_number}?text={quote(message)}' if phone_number else f'https://wa.me/?text={quote(message)}'
	return render(request, 'orders/confirmation.html', {
		'order': order,
		'items': items,
		'whatsapp_url': whatsapp_url,
		'certificate_url': reverse('orders:verify_certificate', args=[order.certificate_id]),
		'seo_title': f'Order {order.reference} Confirmed | Ahmaan Art Gallery',
		'seo_description': f'Your Ahmaan Art Gallery order {order.reference} has been received. Review your order details and authenticity certificate.',
	})


def track_order(request):
	form = OrderTrackingForm(request.POST or None)
	order = None
	if request.method == 'POST' and form.is_valid():
		order = Order.objects.prefetch_related('items').filter(
			reference=form.cleaned_data['order_id'].strip(),
			customer_phone=form.cleaned_data['phone'].strip(),
		).first()
		if not order:
			form.add_error(None, 'We could not find an order with that ID and phone number.')
	return render(request, 'orders/track.html', {'form': form, 'order': order, 'timeline': _timeline(order) if order else []})


def verify_certificate(request, certificate_id):
	order = get_object_or_404(Order.objects.prefetch_related('items__artwork__artist'), certificate_id=certificate_id)
	return render(request, 'orders/verify_certificate.html', {'order': order})


def download_certificate(request, certificate_id):
	order = get_object_or_404(Order, certificate_id=certificate_id)
	if not order.certificate_file:
		raise Http404
	return FileResponse(order.certificate_file.open('rb'), as_attachment=True, filename=f'Ahmaan-Certificate-{order.certificate_id}.pdf')


def _timeline(order):
	steps = [
		('pending', 'Order received'),
		('confirmed', 'Confirmed'),
		('in_progress', 'In progress'),
		('shipped', 'Shipped'),
		('delivered', 'Delivered'),
	]
	status = 'in_progress' if order.status == Order.Status.PROCESSING else 'delivered' if order.status == Order.Status.COMPLETED else order.status
	current_index = next((index for index, (value, _) in enumerate(steps) if value == status), -1)
	return [{'value': value, 'label': label, 'complete': index <= current_index, 'current': index == current_index} for index, (value, label) in enumerate(steps)]


def order_history(request):
	if not request.user.is_authenticated:
		return redirect('gallery:login')
	orders = request.user.orders.prefetch_related('items').all()
	return render(request, 'orders/history.html', {'orders': orders})


def analytics_data():
	orders = Order.objects.all()
	return {
		'order_count': orders.count(),
		'revenue': orders.filter(payment_status=Order.PaymentStatus.PAID).aggregate(value=Sum('total'))['value'] or Decimal('0.00'),
		'pending_count': orders.filter(status=Order.Status.PENDING).count(),
		'status_counts': {value: orders.filter(status=value).count() for value, _ in Order.Status.choices},
		'top_items': OrderItem.objects.values('title_at_order').annotate(quantity=Sum('quantity')).order_by('-quantity')[:5],
	}








