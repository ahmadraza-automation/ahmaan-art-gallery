import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify

from core.images import optimize_uploaded_image


class Artist(models.Model):
	name = models.CharField(max_length=120)
	slug = models.SlugField(max_length=140, unique=True, blank=True)
	city = models.CharField(max_length=100, blank=True)
	meta_title = models.CharField(max_length=70, blank=True)
	meta_description = models.CharField(max_length=320, blank=True)
	photo = models.ImageField(upload_to='artists/', blank=True)
	bio = models.TextField(blank=True)
	specialty = models.CharField(max_length=160, blank=True)
	instagram_url = models.URLField(blank=True)
	website_url = models.URLField(blank=True)
	other_social_links = models.JSONField(default=dict, blank=True)
	interview_article = models.ForeignKey('core.JournalPost', on_delete=models.SET_NULL, null=True, blank=True, related_name='interviewed_artists')

	class Meta:
		ordering = ['name']

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		optimize_uploaded_image(self, 'photo')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.name


class Category(models.Model):
	name = models.CharField(max_length=100, unique=True)
	slug = models.SlugField(max_length=110, unique=True, blank=True)
	description = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['order', 'name']
		verbose_name_plural = 'categories'

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.name


class Collection(models.Model):
	name = models.CharField(max_length=140)
	slug = models.SlugField(max_length=160, unique=True, blank=True)
	meta_title = models.CharField(max_length=70, blank=True)
	meta_description = models.CharField(max_length=320, blank=True)
	cover_image = models.ImageField(upload_to='collections/', blank=True)
	short_description = models.CharField(max_length=280, blank=True)
	is_featured = models.BooleanField(default=False)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['order', 'name']

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		optimize_uploaded_image(self, 'cover_image')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.name


class Room(models.Model):
	name = models.CharField(max_length=100)
	slug = models.SlugField(max_length=120, unique=True, blank=True)
	short_description = models.CharField(max_length=240, blank=True)
	image = models.ImageField(upload_to='rooms/', blank=True)
	meta_title = models.CharField(max_length=70, blank=True)
	meta_description = models.CharField(max_length=320, blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'name']

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		optimize_uploaded_image(self, 'image')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.name


class PriceRange(models.Model):
	label = models.CharField(max_length=100)
	minimum_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
	maximum_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'pk']

	def clean(self):
		super().clean()
		if self.maximum_price is not None and self.maximum_price < self.minimum_price:
			raise ValidationError({'maximum_price': 'Maximum price must be greater than or equal to the minimum price.'})

	def __str__(self):
		return self.label


class SizeOption(models.Model):
	name = models.CharField(max_length=80, unique=True)
	price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	width = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
	height = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class FrameOption(models.Model):
	name = models.CharField(max_length=80, unique=True)
	price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class CanvasType(models.Model):
	name = models.CharField(max_length=100, unique=True)
	description = models.CharField(max_length=240, blank=True)
	price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class Artwork(models.Model):
	class Status(models.TextChoices):
		AVAILABLE = 'available', 'Available'
		RESERVED = 'reserved', 'Reserved'
		SOLD = 'sold', 'Sold'

	class Space(models.TextChoices):
		HOME = 'home', 'Home'
		CAFE = 'cafe', 'Cafe'
		OFFICE = 'office', 'Office'
		GALLERY = 'gallery', 'Gallery'

	title = models.CharField(max_length=180)
	slug = models.SlugField(max_length=200, unique=True, blank=True)
	meta_title = models.CharField(max_length=70, blank=True)
	meta_description = models.CharField(max_length=320, blank=True)
	mood_tagline = models.CharField(max_length=180)
	story = models.TextField()
	artist = models.ForeignKey(Artist, on_delete=models.PROTECT, related_name='artworks')
	category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='artworks')
	collections = models.ManyToManyField(Collection, blank=True, related_name='artworks')
	rooms = models.ManyToManyField(Room, blank=True, related_name='artworks')
	medium = models.CharField(max_length=140)
	year = models.PositiveSmallIntegerField(null=True, blank=True)
	width = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
	height = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
	base_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
	style_tags = models.JSONField(default=list, blank=True)
	subject_tags = models.JSONField(default=list, blank=True)
	color_palette_tags = models.JSONField(default=list, blank=True)
	mood_tags = models.JSONField(default=list, blank=True)
	space_tags = models.JSONField(default=list, blank=True)
	is_one_of_a_kind = models.BooleanField(default=True)
	quantity = models.PositiveIntegerField(default=1)
	is_limited_edition = models.BooleanField(default=False)
	edition_size = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
	remaining = models.PositiveIntegerField(null=True, blank=True)
	status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE)
	reserved_until = models.DateTimeField(null=True, blank=True)
	is_featured = models.BooleanField(default=False)
	is_best_seller = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-is_featured', '-created_at']
		indexes = [models.Index(fields=['status', 'is_featured']), models.Index(fields=['category', 'status'])]

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.title)
		super().save(*args, **kwargs)

	@property
	def reservation_is_active(self):
		return self.status == self.Status.RESERVED and self.reserved_until and self.reserved_until > timezone.now()

	def __str__(self):
		return self.title


class ArtworkImage(models.Model):
	artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='images')
	image = models.ImageField(upload_to='artworks/')
	alt_text = models.CharField(max_length=240, blank=True)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['order', 'pk']

	def save(self, *args, **kwargs):
		self.alt_text = self.alt_text.strip() or f'{self.artwork.title} original artwork'
		optimize_uploaded_image(self, 'image')
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.artwork}: image {self.order + 1}'


class Review(models.Model):
	artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='reviews')
	name = models.CharField(max_length=120)
	rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
	text = models.TextField()
	photo = models.ImageField(upload_to='reviews/', blank=True)
	is_approved = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def save(self, *args, **kwargs):
		optimize_uploaded_image(self, 'photo')
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.name} - {self.artwork}'


class ArtworkOffer(models.Model):
	artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='offers')
	name = models.CharField(max_length=120)
	phone = models.CharField(max_length=32)
	email = models.EmailField()
	offer_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.name} offered PKR {self.offer_price} for {self.artwork}'


class Wishlist(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='artwork_wishlist')
	artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='wishlisted_by')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		constraints = [models.UniqueConstraint(fields=['user', 'artwork'], name='unique_user_artwork_wishlist')]

	def __str__(self):
		return f'{self.user} saved {self.artwork}'


class NotifyRequest(models.Model):
	class Channel(models.TextChoices):
		EMAIL = 'email', 'Email'
		WHATSAPP = 'whatsapp', 'WhatsApp'

	channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.EMAIL)
	email = models.EmailField(blank=True)
	whatsapp = models.CharField(max_length=30, blank=True)
	artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, null=True, blank=True, related_name='notify_requests')
	category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='notify_requests')
	is_notified = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.get_channel_display()} notification request'


class ArtworkBundle(models.Model):
	name = models.CharField(max_length=160)
	slug = models.SlugField(max_length=180, unique=True, blank=True)
	short_description = models.CharField(max_length=280, blank=True)
	artworks = models.ManyToManyField(Artwork, through='ArtworkBundleItem', related_name='bundles')
	bundle_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
	is_featured = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-is_featured', '-created_at']

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		super().save(*args, **kwargs)

	@property
	def individual_total(self):
		return sum((item.artwork.base_price for item in self.bundle_items.select_related('artwork')), start=0)

	@property
	def savings(self):
		return self.individual_total - self.bundle_price

	def clean(self):
		if not self.pk:
			return
		items = list(self.bundle_items.select_related('artwork'))
		if items and len(items) not in (2, 3):
			raise ValidationError({'artworks': 'A curated set must contain exactly two or three artworks.'})
		if items and self.bundle_price >= sum((item.artwork.base_price for item in items), start=0):
			raise ValidationError({'bundle_price': 'The set price must be lower than the combined artwork prices.'})

	def __str__(self):
		return self.name


class ArtworkBundleItem(models.Model):
	bundle = models.ForeignKey(ArtworkBundle, on_delete=models.CASCADE, related_name='bundle_items')
	artwork = models.ForeignKey(Artwork, on_delete=models.PROTECT, related_name='bundle_items')
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['order', 'pk']
		constraints = [models.UniqueConstraint(fields=['bundle', 'artwork'], name='unique_artwork_per_bundle')]

	def clean(self):
		existing_items = self.bundle.bundle_items.exclude(pk=self.pk)
		if existing_items.count() >= 3:
			raise ValidationError('A curated set can contain no more than three artworks.')
		if existing_items.count() + 1 in (2, 3):
			combined_price = sum(existing_items.values_list('artwork__base_price', flat=True), start=self.artwork.base_price)
			if self.bundle.bundle_price >= combined_price:
				raise ValidationError('The set price must be lower than the combined artwork prices.')

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.bundle}: {self.artwork}'
