from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.validators import FileExtensionValidator
import uuid


class ArtworkCategory(models.Model):
	name = models.CharField(max_length=80, unique=True)
	slug = models.SlugField(max_length=60, unique=True)
	is_active = models.BooleanField(default=True)
	sort_order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['sort_order', 'name']
		verbose_name_plural = 'artwork categories'

	def __str__(self):
		return self.name


class Artwork(models.Model):
	class Category:
		OIL_PAINTING = 'oil-painting'
		CALLIGRAPHY = 'calligraphy'
		DIGITAL_ART = 'digital-art'
		HANDMADE_SKETCH = 'handmade-sketch'
		CUSTOM_PORTRAIT = 'custom-portrait'
		BESPOKE_WORKS = 'bespoke-works'
		PAINTING = 'painting'
		SCULPTURE = 'sculpture'
		PHOTOGRAPHY = 'photography'
		MIXED_MEDIA = 'mixed-media'
		choices = (
			(OIL_PAINTING, 'Oil Paintings'),
			(CALLIGRAPHY, 'Calligraphy'),
			(DIGITAL_ART, 'Digital Art'),
			(HANDMADE_SKETCH, 'Handmade Sketches'),
			(CUSTOM_PORTRAIT, 'Custom Portraits'),
		)
		values = tuple(value for value, _ in choices)
		legacy_values = (PAINTING, SCULPTURE, PHOTOGRAPHY, MIXED_MEDIA)

	title = models.CharField(max_length=160)
	slug = models.SlugField(max_length=180, unique=True, blank=True)
	meta_title = models.CharField(max_length=70, blank=True)
	meta_description = models.CharField(max_length=320, blank=True)
	artist = models.CharField(max_length=120)
	category = models.ForeignKey(ArtworkCategory, on_delete=models.PROTECT, related_name='artworks')
	description = models.TextField()
	image_url = models.URLField(max_length=500)
	medium = models.CharField(max_length=120, blank=True)
	dimensions = models.CharField(max_length=80, blank=True)
	year = models.PositiveSmallIntegerField(null=True, blank=True)
	price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	is_available = models.BooleanField(default=True)
	is_featured = models.BooleanField(default=False)
	is_popular = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-is_featured', '-created_at']

	def save(self, *args, **kwargs):
		if not self.slug:
			base_slug = slugify(self.title)
			self.slug = base_slug
			suffix = 2
			while Artwork.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
				self.slug = f'{base_slug}-{suffix}'
				suffix += 1
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.title} by {self.artist}'

	def get_category_display(self):
		return self.category.name


class LegacyWishlist(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='legacy_artwork_wishlist')
	artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='saved_by')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		constraints = [models.UniqueConstraint(fields=['user', 'artwork'], name='unique_user_legacy_artwork_wishlist')]

	def __str__(self):
		return f'{self.user} saved {self.artwork}'


class Order(models.Model):
	class OrderType(models.TextChoices):
		ARTWORK = 'artwork', 'Artwork order'
		COMMISSION = 'commission', 'Custom commission'

	class Size(models.TextChoices):
		SMALL = 'small', 'Small'
		MEDIUM = 'medium', 'Medium'
		LARGE = 'large', 'Large'

	class Frame(models.TextChoices):
		NONE = 'none', 'No frame'
		BLACK = 'black', 'Black'
		WHITE = 'white', 'White'
		WOOD = 'wood', 'Natural wood'

	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		CONFIRMED = 'confirmed', 'Confirmed'
		COMPLETED = 'completed', 'Completed'
		CANCELLED = 'cancelled', 'Cancelled'

	class PaymentMethod(models.TextChoices):
		COD = 'cod', 'Cash on delivery'

	artwork = models.ForeignKey(Artwork, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='gallery_orders')
	order_type = models.CharField(max_length=16, choices=OrderType.choices)
	art_category = models.CharField(max_length=60)
	requested_title = models.CharField(max_length=160, blank=True)
	customer_name = models.CharField(max_length=120)
	customer_email = models.EmailField()
	customer_phone = models.CharField(max_length=30)
	delivery_address = models.TextField()
	size = models.CharField(max_length=10, choices=Size.choices)
	frame = models.CharField(max_length=10, choices=Frame.choices, default=Frame.NONE)
	quantity = models.PositiveSmallIntegerField(default=1)
	checkout_reference = models.UUIDField(default=uuid.uuid4, db_index=True)
	payment_method = models.CharField(max_length=8, choices=PaymentMethod.choices, default=PaymentMethod.COD)
	custom_additions = models.TextField(blank=True)
	client_image = models.ImageField(
		upload_to='commission_uploads/',
		blank=True,
		validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
	)
	price_at_order = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'Order #{self.pk} - {self.get_order_type_display()} for {self.customer_name}'

	def get_art_category_display(self):
		return ArtworkCategory.objects.filter(slug=self.art_category).values_list('name', flat=True).first() or self.art_category


class GalleryProfile(models.Model):
	artist_name = models.CharField(max_length=120, blank=True)
	artist_background = models.TextField(blank=True)
	gallery_ethos = models.TextField(blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'gallery profile'
		verbose_name_plural = 'gallery profile'

	def __str__(self):
		return 'Gallery profile'


class ContactInquiry(models.Model):
	name = models.CharField(max_length=120)
	email = models.EmailField()
	subject = models.CharField(max_length=160)
	message = models.TextField()
	submitted_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-submitted_at']

	def __str__(self):
		return f'{self.subject} from {self.name}'
