from urllib.parse import quote
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Avg, Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings

from catalog.models import Artwork as CatalogArtwork, ArtworkBundle, Collection as ArtCollection, PriceRange, Room
from core.forms import CustomerReviewForm
from core.models import BrandStory, CustomerReview, HeroSlide, InstagramImage, JournalPost, PressMention, SiteSettings, Testimonial, TrustFeature, WelcomeOffer
from core.seo import schema_json
from core.security import rate_limit
from .forms import CheckoutForm, CommissionRequestForm, ContactInquiryForm, UserProfileForm
from .models import Artwork, ArtworkCategory, GalleryProfile, Order
from .pricing import SIZE_MULTIPLIERS, artwork_price


def _whatsapp_url(message):
    phone = ''.join(character for character in settings.WHATSAPP_NUMBER if character.isdigit())
    if phone:
        return f'https://wa.me/{phone}?text={quote(message)}'
    return f'https://wa.me/?text={quote(message)}'


def home(request, shop_page=False):
    artworks = Artwork.objects.select_related('category')
    category = request.GET.get('category', '')
    categories = ArtworkCategory.objects.filter(is_active=True)
    if category and categories.filter(slug=category).exists():
        artworks = artworks.filter(category__slug=category)
    search = request.GET.get('q', '').strip()
    if search:
        artworks = artworks.filter(Q(title__icontains=search) | Q(artist__icontains=search) | Q(category__name__icontains=search))
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    for field, value, comparison in (('min_price', min_price, 'gte'), ('max_price', max_price, 'lte')):
        if value:
            try:
                amount = Decimal(value)
                if amount.is_finite() and amount >= 0:
                    artworks = artworks.filter(**{f'price__{comparison}': amount})
            except InvalidOperation:
                pass
    availability = request.GET.get('availability', '')
    if availability == 'in-stock':
        artworks = artworks.filter(is_available=True)
    elif availability == 'sold-out':
        artworks = artworks.filter(is_available=False)
    sort = request.GET.get('sort', '')
    if sort == 'price-low':
        artworks = artworks.order_by('price', 'title')
    elif sort == 'price-high':
        artworks = artworks.order_by('-price', 'title')
    max_catalog_price = Artwork.objects.aggregate(maximum=Max('price'))['maximum'] or Decimal('100000')
    featured = Artwork.objects.filter(is_featured=True).first()
    popular = Artwork.objects.filter(is_popular=True, is_available=True)[:3]
    context = {
        'artworks': artworks,
        'categories': categories,
        'active_category': category,
        'availability': availability,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
        'max_catalog_price': max_catalog_price,
        'featured': featured,
        'popular': popular,
        'search': search,
        'shop_page': shop_page,
    }
    if not shop_page:
        catalog_artworks = CatalogArtwork.objects.select_related('artist', 'category').prefetch_related('images', 'collections')
        featured_works = catalog_artworks.filter(is_featured=True)
        best_sellers = catalog_artworks.filter(is_best_seller=True)[:4]
        if not best_sellers:
            best_sellers = catalog_artworks.filter(status=CatalogArtwork.Status.AVAILABLE)[:4]
        spotlight_artwork = featured_works.first() or catalog_artworks.first()
        colors = []
        spaces = []
        for artwork in catalog_artworks:
            for color in artwork.color_palette_tags:
                if color not in colors:
                    colors.append(color)
            for space in artwork.space_tags:
                if space not in spaces:
                    spaces.append(space)
        context.update({
            'hero_slides': HeroSlide.objects.filter(is_active=True).select_related('video_media'),
            'site_settings': SiteSettings.objects.first(),
            'welcome_offer': WelcomeOffer.objects.filter(is_active=True).first(),
            'featured_works': featured_works[:4],
            'best_sellers': best_sellers,
            'featured_bundles': ArtworkBundle.objects.filter(is_active=True, is_featured=True)[:2],
            'new_arrivals': catalog_artworks.order_by('-created_at')[:4],
            'new_this_week': catalog_artworks.filter(status=CatalogArtwork.Status.AVAILABLE).order_by('-created_at')[:8],
            'art_collections': ArtCollection.objects.order_by('order', 'name')[:6],
            'curator_collections': ArtCollection.objects.filter(is_featured=True).order_by('order', 'name')[:8],
            'discovery_rooms': Room.objects.filter(is_active=True)[:4],
            'price_ranges': PriceRange.objects.filter(is_active=True),
            'shop_spaces': spaces[:4],
            'palette_colors': colors[:8],
            'spotlight_artist': spotlight_artwork.artist if spotlight_artwork else None,
            'spotlight_artworks': catalog_artworks.filter(artist=spotlight_artwork.artist)[:3] if spotlight_artwork else [],
            'instagram_images': InstagramImage.objects.filter(is_active=True)[:6],
            'testimonials': Testimonial.objects.filter(is_published=True)[:6],
            'collector_reviews': CustomerReview.objects.filter(is_approved=True).select_related('artwork')[:12],
            'collector_review_average': CustomerReview.objects.filter(is_approved=True).aggregate(average=Avg('rating'))['average'],
            'collector_review_form': CustomerReviewForm(),
            'trust_features': TrustFeature.objects.filter(is_active=True)[:4],
            'brand_story': BrandStory.objects.filter(is_active=True).first(),
            'press_mentions': PressMention.objects.filter(is_active=True),
            'journal_posts': JournalPost.objects.filter(is_published=True, published_at__lte=timezone.now()).order_by('-published_at')[:3],
        })
    template_name = 'gallery/home.html' if shop_page else 'gallery/home_editorial.html'
    return render(request, template_name, context)


@require_POST
@rate_limit(6, period=3600)
def collector_review_submit(request):
    form = CustomerReviewForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, 'Thank you. Your review has been sent to the gallery for approval.')
    else:
        messages.error(request, 'Please check the review details and try again.')
    return redirect('/#customer-reviews')


def shop(request):
    return home(request, shop_page=True)


def artwork_detail(request, slug):
    artwork = get_object_or_404(Artwork.objects.select_related('category'), slug=slug)
    product_url = f"{settings.PUBLIC_SITE_URL.rstrip('/')}/artwork/{artwork.slug}/"
    seo_description = artwork.meta_description or f'{artwork.description[:220]} Original {artwork.get_category_display().lower()} by {artwork.artist} at Ahmaan Art Gallery Pakistan.'
    product_data = {
        '@context': 'https://schema.org', '@type': 'Product',
        'name': artwork.title, 'description': seo_description,
        'image': artwork.image_url, 'category': artwork.get_category_display(),
        'brand': {'@type': 'Brand', 'name': 'Ahmaan Art Gallery'}, 'url': product_url,
    }
    if artwork.price is not None:
        product_data['offers'] = {
            '@type': 'Offer', 'url': product_url, 'priceCurrency': 'PKR',
            'price': str(artwork.price),
            'availability': 'https://schema.org/InStock' if artwork.is_available else 'https://schema.org/OutOfStock',
        }
    return render(request, 'gallery/artwork_detail.html', {
        'artwork': artwork,
        'seo_title': artwork.meta_title or f'{artwork.title} {artwork.get_category_display()} | Ahmaan Art Gallery Pakistan',
        'seo_description': seo_description,
        'seo_image': artwork.image_url,
        'product_jsonld': schema_json(product_data),
        'breadcrumb_jsonld': schema_json({
            '@context': 'https://schema.org', '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': settings.PUBLIC_SITE_URL.rstrip('/') + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Artworks', 'item': settings.PUBLIC_SITE_URL.rstrip('/') + '/shop/'},
                {'@type': 'ListItem', 'position': 3, 'name': artwork.title, 'item': product_url},
            ],
        }),
        'size_options': [
            {'value': value, 'label': label, 'multiplier': SIZE_MULTIPLIERS[value]}
            for value, label in Order.Size.choices
        ],
        'frame_options': Order.Frame.choices,
    })


def artwork_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    artworks = Artwork.objects.filter(is_available=True).filter(
        Q(title__icontains=query) | Q(artist__icontains=query) | Q(category__name__icontains=query)
    ).select_related('category')[:8]
    return JsonResponse({'results': [{
        'title': artwork.title,
        'artist': artwork.artist,
        'category': artwork.category.name,
        'url': f'/artwork/{artwork.slug}/',
        'price': f'PKR {artwork.price:,.0f}' if artwork.price is not None else 'Price on request',
    } for artwork in artworks]})


@require_POST
def cart_add(request):
    artwork = get_object_or_404(Artwork, pk=request.POST.get('artwork_id'), is_available=True)
    size = request.POST.get('size', Order.Size.MEDIUM)
    frame = request.POST.get('frame', Order.Frame.NONE)
    if size not in Order.Size.values or frame not in Order.Frame.values:
        messages.error(request, 'Choose a valid size and frame.')
        return redirect('gallery:artwork_detail', slug=artwork.slug)

    cart = request.session.get('gallery_cart', [])
    additions = request.POST.get('custom_additions', '').strip()[:2000]
    line = next((item for item in cart if item['artwork_id'] == artwork.pk and item['size'] == size and item['frame'] == frame and item['custom_additions'] == additions), None)
    if line:
        line['quantity'] = min(20, line['quantity'] + 1)
    else:
        cart.append({'id': str(uuid4()), 'artwork_id': artwork.pk, 'size': size, 'frame': frame, 'custom_additions': additions, 'quantity': 1})
    request.session['gallery_cart'] = cart
    return redirect(f"/artwork/{artwork.slug}/?added=1#cart-panel")


@require_POST
def cart_update(request, line_id):
    cart = request.session.get('gallery_cart', [])
    try:
        quantity = int(request.POST.get('quantity', '1'))
    except ValueError:
        quantity = 1
    for item in cart:
        if item.get('id') == line_id:
            if quantity <= 0:
                cart.remove(item)
            else:
                item['quantity'] = min(20, quantity)
            break
    request.session['gallery_cart'] = cart
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('gallery:shop')


@require_POST
def cart_remove(request, line_id):
    return cart_update(request, line_id)


@rate_limit(8, period=60)
def checkout(request):
    if request.session.get('catalog_cart'):
        from orders.views import checkout as payment_checkout

        return payment_checkout(request)
    cart = request.session.get('gallery_cart', [])
    if not cart:
        messages.info(request, 'Your cart is empty.')
        return redirect('gallery:shop')

    initial = {}
    if request.user.is_authenticated:
        initial = {
            'customer_name': request.user.get_full_name() or request.user.username,
            'customer_email': request.user.email,
        }
    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        artwork_ids = {item.get('artwork_id') for item in cart if isinstance(item, dict)}
        artworks = Artwork.objects.filter(pk__in=artwork_ids, is_available=True).select_related('category')
        artworks_by_id = {artwork.pk: artwork for artwork in artworks}
        if len(artworks_by_id) != len(artwork_ids):
            messages.error(request, 'Some cart items are no longer available. Please review your cart.')
            return redirect('gallery:shop')

        reference = uuid4()
        created_orders = []
        for item in cart:
            artwork = artworks_by_id[item['artwork_id']]
            price = artwork_price(artwork, item['size'])
            created_orders.append(Order.objects.create(
                artwork=artwork,
                user=request.user if request.user.is_authenticated else None,
                order_type=Order.OrderType.ARTWORK,
                art_category=artwork.category.slug,
                requested_title=artwork.title,
                customer_name=form.cleaned_data['customer_name'],
                customer_email=form.cleaned_data['customer_email'],
                customer_phone=form.cleaned_data['customer_phone'],
                delivery_address=form.cleaned_data['delivery_address'],
                size=item['size'],
                frame=item['frame'],
                quantity=item['quantity'],
                custom_additions=item['custom_additions'],
                price_at_order=price,
                checkout_reference=reference,
            ))
        request.session['gallery_cart'] = []
        request.session['gallery_checkout_reference'] = str(reference)
        return redirect('gallery:checkout_complete', reference=reference)

    return render(request, 'gallery/checkout.html', {'form': form})


def checkout_complete(request, reference):
    orders = Order.objects.filter(checkout_reference=reference).select_related('artwork', 'user')
    first_order = orders.first()
    if not first_order:
        return redirect('gallery:home')
    is_owner = request.user.is_authenticated and orders.filter(user=request.user).exists()
    has_session = request.session.get('gallery_checkout_reference') == str(reference)
    if not is_owner and not has_session:
        return redirect('gallery:home')

    items = []
    message_lines = [f"Hello Ahmaan Art Gallery, I'd like to confirm order {str(reference)[:8]}:"]
    for order in orders:
        items.append({'order': order, 'line_total': order.price_at_order * order.quantity if order.price_at_order is not None else None})
        message_lines.append(f"- {order.quantity} x {order.requested_title}; {order.get_size_display()}, {order.get_frame_display()}; {order.custom_additions or 'no extra notes'}")
    message_lines.extend([
        f"Name: {first_order.customer_name}",
        f"Phone: {first_order.customer_phone}",
        f"Delivery: {first_order.delivery_address}",
        'Payment: Cash on delivery',
    ])
    return render(request, 'gallery/order_complete.html', {
        'order': first_order,
        'items': items,
        'whatsapp_url': _whatsapp_url('\n'.join(message_lines)),
        'seo_title': f'Order {str(reference)[:8]} Received | Ahmaan Art Gallery',
        'seo_description': f'Order {str(reference)[:8]} for original artwork has been received by Ahmaan Art Gallery. Review your order details and contact the gallery.',
    })


@rate_limit(8, period=60)
def commission(request):
    if request.method == 'POST' and request.POST.get('website'):
        return redirect('gallery:commission')
    initial = {}
    artwork_slug = request.GET.get('artwork', '').strip()
    if artwork_slug:
        similar_artwork = CatalogArtwork.objects.select_related('category').filter(slug=artwork_slug).first()
        if similar_artwork:
            initial['requested_title'] = f'A piece in the spirit of {similar_artwork.title}'
            initial['custom_additions'] = f'I am interested in a similar mood: {similar_artwork.mood_tagline}'
            matching_category = ArtworkCategory.objects.filter(name__iexact=similar_artwork.category.name, is_active=True).first()
            if matching_category:
                initial['art_category'] = matching_category.slug
    form = CommissionRequestForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        order = form.save(commit=False)
        order.user = request.user if request.user.is_authenticated else None
        order.order_type = Order.OrderType.COMMISSION
        order.save()
        request.session['gallery_order_id'] = order.pk
        return redirect('gallery:order_complete', order_id=order.pk)
    return render(request, 'gallery/commission.html', {'form': form})


def order_complete(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    is_owner = request.user.is_authenticated and order.user_id == request.user.pk
    has_session = request.session.get('gallery_order_id') == order.pk
    if not is_owner and not has_session:
        return redirect('gallery:home')
    message = '\n'.join([
        f"Hello Ahmaan Art Gallery, I submitted order #{order.pk} for {order.requested_title or order.get_art_category_display()}.",
        f"Size: {order.get_size_display()}; frame: {order.get_frame_display()}",
        f"Notes: {order.custom_additions or 'none'}",
        f"Name: {order.customer_name}; phone: {order.customer_phone}",
        f"Delivery: {order.delivery_address}",
        'Payment: Cash on delivery',
    ])
    return render(request, 'gallery/order_complete.html', {
        'order': order,
        'items': [{'order': order, 'line_total': order.price_at_order}],
        'whatsapp_url': _whatsapp_url(message),
        'seo_title': f'Commission Request {order.pk} Received | Ahmaan Art Gallery' if order.order_type == Order.OrderType.COMMISSION else f'Order {order.pk} Received | Ahmaan Art Gallery',
        'seo_description': f'Your custom art commission request {order.pk} has been received by Ahmaan Art Gallery. We will review the details and follow up soon.' if order.order_type == Order.OrderType.COMMISSION else f'Your original artwork order {order.pk} has been received by Ahmaan Art Gallery. Review your order details and contact the gallery.',
    })


def about(request):
    return render(request, 'gallery/about.html', {'artist_profile': GalleryProfile.objects.first()})


@rate_limit(5, period=300)
def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('gallery:home')
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def profile(request):
    form = UserProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('gallery:profile')
    orders = request.user.gallery_orders.select_related('artwork').order_by('-created_at')
    return render(request, 'gallery/profile.html', {'form': form, 'orders': orders})


@rate_limit(8, period=60)
def contact(request):
    if request.method == 'POST' and request.POST.get('website'):
        return redirect('gallery:contact')
    topic = request.GET.get('topic', '').strip()
    subject = request.GET.get('subject', '').strip() or {
        'delivery': 'Delivery and shipping',
        'returns': 'Returns and exchanges',
        'privacy': 'Privacy question',
        'journal': 'Journal / editorial inquiry',
    }.get(topic, '')
    form = ContactInquiryForm(
        request.POST or None,
        initial={'subject': subject},
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Thank you. Your message has been sent to the gallery.')
        return redirect('gallery:contact')
    return render(request, 'gallery/contact.html', {'form': form})
