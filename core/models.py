from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from core.images import optimize_uploaded_image


class SiteSettings(models.Model):
	announcement_bar_text = models.CharField(max_length=240, blank=True)
	announcement_bar_enabled = models.BooleanField(default=True)
	homepage_artists_count = models.PositiveIntegerField(default=0)
	homepage_artworks_count = models.PositiveIntegerField(default=0)
	homepage_cities_delivered_count = models.PositiveIntegerField(default=0)
	homepage_happy_collectors_count = models.PositiveIntegerField(default=0)
	payment_badge_cod = models.BooleanField(default=True)
	payment_badge_bank_transfer = models.BooleanField(default=True)
	payment_badge_jazzcash = models.BooleanField(default=True)
	payment_badge_easypaisa = models.BooleanField(default=True)
	flat_shipping_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
	free_shipping_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
	whatsapp_number = models.CharField(max_length=32, blank=True)
	address = models.TextField(blank=True)
	opening_hours = models.CharField(max_length=240, blank=True)
	instagram_url = models.URLField(blank=True)
	facebook_url = models.URLField(blank=True)
	pinterest_url = models.URLField(blank=True)
	other_social_links = models.JSONField(default=dict, blank=True)
	minimum_delivery_days = models.PositiveSmallIntegerField(default=3)
	maximum_delivery_days = models.PositiveSmallIntegerField(default=7)
	bank_name = models.CharField(max_length=120, blank=True)
	bank_account_title = models.CharField(max_length=140, blank=True)
	bank_account_number = models.CharField(max_length=80, blank=True)
	bank_iban = models.CharField(max_length=80, blank=True)
	jazzcash_account_title = models.CharField(max_length=140, blank=True)
	jazzcash_number = models.CharField(max_length=40, blank=True)
	easypaisa_account_title = models.CharField(max_length=140, blank=True)
	easypaisa_number = models.CharField(max_length=40, blank=True)
	minimum_offer_percent = models.PositiveSmallIntegerField(default=70, validators=[MinValueValidator(1), MaxValueValidator(100)])
	payment_instructions = models.TextField(blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'site settings'
		verbose_name_plural = 'site settings'

	def __str__(self):
		return 'Site settings'


class HeroSlide(models.Model):
	title = models.CharField(max_length=160)
	subtitle = models.CharField(max_length=240, blank=True)
	image = models.ImageField(upload_to='hero-slides/')
	button_text = models.CharField(max_length=50, blank=True)
	button_url = models.CharField(max_length=300, blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'pk']

	def save(self, *args, **kwargs):
		optimize_uploaded_image(self, 'image')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.title


class HeroSlideVideo(models.Model):
	slide = models.OneToOneField(HeroSlide, on_delete=models.CASCADE, related_name='video_media')
	video_url = models.URLField(help_text='Use a directly playable MP4/WebM URL. The slide image is used as its poster.')
	is_enabled = models.BooleanField(default=True)

	def __str__(self):
		return f'Video for {self.slide}'


class Banner(models.Model):
	title = models.CharField(max_length=160)
	image = models.ImageField(upload_to='banners/', blank=True)
	button_text = models.CharField(max_length=50, blank=True)
	button_url = models.CharField(max_length=300, blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'pk']

	def save(self, *args, **kwargs):
		optimize_uploaded_image(self, 'image')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.title


class InstagramImage(models.Model):
	image = models.ImageField(upload_to='instagram/')
	caption = models.CharField(max_length=240, blank=True)
	post_url = models.URLField(blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'pk']

	def save(self, *args, **kwargs):
		optimize_uploaded_image(self, 'image')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.caption or f'Instagram image #{self.pk or "new"}'


class Testimonial(models.Model):
	name = models.CharField(max_length=120)
	location = models.CharField(max_length=120, blank=True)
	is_verified = models.BooleanField(default=True)
	quote = models.TextField()
	rating = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1)])
	is_published = models.BooleanField(default=False)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['order', 'pk']

	def __str__(self):
		return self.name


class CustomerReview(models.Model):
	artwork = models.ForeignKey('catalog.Artwork', on_delete=models.SET_NULL, null=True, blank=True, related_name='collector_reviews')
	name = models.CharField(max_length=120)
	city = models.CharField(max_length=120)
	rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
	title = models.CharField(max_length=160)
	text = models.TextField()
	is_verified = models.BooleanField(default=False)
	is_approved = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.name} - {self.title}'


class TrustFeature(models.Model):
	title = models.CharField(max_length=120)
	description = models.CharField(max_length=280)
	icon = models.CharField(max_length=40, blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'pk']

	def __str__(self):
		return self.title


class BrandStory(models.Model):
	heading = models.CharField(max_length=180)
	story = models.TextField()
	image = models.ImageField(upload_to='brand-story/', blank=True)
	button_text = models.CharField(max_length=60, default='Our story')
	is_active = models.BooleanField(default=True)

	def save(self, *args, **kwargs):
		optimize_uploaded_image(self, 'image')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.heading


class PressMention(models.Model):
	publication = models.CharField(max_length=120)
	logo = models.ImageField(upload_to='press/', blank=True)
	url = models.URLField(blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'pk']

	def save(self, *args, **kwargs):
		optimize_uploaded_image(self, 'logo')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.publication


class FAQ(models.Model):
	class Category(models.TextChoices):
		BUYING = 'buying', 'Buying'
		SHIPPING = 'shipping', 'Shipping'
		RETURNS = 'returns', 'Returns'
		COMMISSIONS = 'commissions', 'Commissions'
		FRAMING = 'framing', 'Framing'
		PAYMENT = 'payment', 'Payment'
		ARTISTS = 'artists', 'Artists'

	category = models.CharField(max_length=16, choices=Category.choices, default=Category.BUYING)
	question = models.CharField(max_length=240)
	answer = models.TextField()
	order = models.PositiveSmallIntegerField(default=0)
	is_published = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'pk']
		verbose_name = 'FAQ'
		verbose_name_plural = 'FAQs'

	def __str__(self):
		return self.question


class WelcomeOffer(models.Model):
	title = models.CharField(max_length=160)
	message = models.CharField(max_length=280)
	offer_code = models.CharField(max_length=40, blank=True)
	button_text = models.CharField(max_length=60, default='Join the newsletter')
	button_url = models.CharField(max_length=300, blank=True)
	is_active = models.BooleanField(default=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']

	def __str__(self):
		return self.title


class NewsletterSubscriber(models.Model):
	email = models.EmailField(unique=True)
	is_active = models.BooleanField(default=True)
	subscribed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-subscribed_at']

	def save(self, *args, **kwargs):
		self.email = self.email.strip().lower()
		super().save(*args, **kwargs)

	def __str__(self):
		return self.email


class JournalPost(models.Model):
	class Category(models.TextChoices):
		ARTIST_INTERVIEWS = 'artist-interviews', 'Artist Interviews'
		ART_BUYING_GUIDES = 'art-buying-guides', 'Art Buying Guides'
		ART_CARE_TIPS = 'art-care-tips', 'Art Care Tips'
		DECOR_IDEAS = 'decor-ideas', 'Decor Ideas'

	title = models.CharField(max_length=180)
	slug = models.SlugField(max_length=200, unique=True, blank=True)
	meta_title = models.CharField(max_length=70, blank=True)
	meta_description = models.CharField(max_length=320, blank=True)
	excerpt = models.CharField(max_length=280)
	body = models.TextField(blank=True)
	category = models.CharField(max_length=24, choices=Category.choices, default=Category.ART_BUYING_GUIDES)
	author = models.CharField(max_length=120, default='Ahmaan Art Gallery')
	cover_image = models.ImageField(upload_to='journal/', blank=True)
	created_at = models.DateTimeField(default=timezone.now)
	published_at = models.DateTimeField(default=timezone.now)
	is_published = models.BooleanField(default=False)

	class Meta:
		ordering = ['-created_at']

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.title)
		optimize_uploaded_image(self, 'cover_image')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.title

	@property
	def reading_time_minutes(self):
		return max(1, (len(self.body.split()) + 199) // 200)


class DesignerInquiry(models.Model):
	name = models.CharField(max_length=120)
	company = models.CharField(max_length=160, blank=True)
	email = models.EmailField()
	phone = models.CharField(max_length=32, blank=True)
	project_type = models.CharField(max_length=160, blank=True)
	message = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.name} - {self.created_at:%Y-%m-%d}'


class ShippingPaymentContent(models.Model):
	heading = models.CharField(max_length=180, default='Shipping & Payments')
	introduction = models.TextField(default='We deliver original artworks across Pakistan and confirm delivery details with every order.')
	nationwide_delivery_text = models.TextField(default='Delivery is available across Pakistan. Our team confirms the destination and estimated arrival before dispatch.')
	cod_text = models.TextField(default='Cash on delivery is available for eligible orders and locations.')
	bank_transfer_text = models.TextField(default='Bank transfer details are shared by the gallery when your order is confirmed.')
	jazzcash_text = models.TextField(default='JazzCash payment instructions are shared by the gallery when your order is confirmed.')
	easypaisa_text = models.TextField(default='Easypaisa payment instructions are shared by the gallery when your order is confirmed.')
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'shipping and payments content'
		verbose_name_plural = 'shipping and payments content'

	def __str__(self):
		return self.heading


class CityDeliveryTime(models.Model):
	city = models.CharField(max_length=100, unique=True)
	minimum_days = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1)])
	maximum_days = models.PositiveSmallIntegerField(default=7, validators=[MinValueValidator(1)])
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'city']

	def clean(self):
		super().clean()
		if self.maximum_days < self.minimum_days:
			from django.core.exceptions import ValidationError
			raise ValidationError({'maximum_days': 'Maximum delivery days must be at least the minimum.'})

	def __str__(self):
		return self.city


class AdSlot(models.Model):
	key = models.SlugField(max_length=60, unique=True, help_text='Stable placement key used by the ad include.')
	name = models.CharField(max_length=120)
	slot_id = models.CharField(max_length=40, help_text='Google AdSense ad unit ID for this placement.')
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class ArtMatchQuestion(models.Model):
	class Key(models.TextChoices):
		ROOM = 'room', 'Room'
		STYLE = 'style', 'Style'
		COLOR = 'color', 'Color'
		BUDGET = 'budget', 'Budget'
		SIZE = 'size', 'Size'

	key = models.CharField(max_length=12, choices=Key.choices, unique=True)
	prompt = models.CharField(max_length=200)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order', 'pk']

	def __str__(self):
		return self.prompt


class ArtMatchOption(models.Model):
	label = models.CharField(max_length=120)
	value = models.CharField(max_length=100)
	minimum_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
	maximum_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
	order = models.PositiveSmallIntegerField(default=0)
	question = models.ForeignKey(ArtMatchQuestion, on_delete=models.CASCADE, related_name='options')

	class Meta:
		ordering = ['order', 'pk']
		constraints = [models.UniqueConstraint(fields=['question', 'value'], name='unique_art_match_option_value')]

	def __str__(self):
		return f'{self.question}: {self.label}'


class ConsultationRequest(models.Model):
	name = models.CharField(max_length=120)
	phone = models.CharField(max_length=32)
	email = models.EmailField(blank=True)
	message = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.name} - {self.created_at:%Y-%m-%d}'


class CuratorAdviceBanner(models.Model):
	heading = models.CharField(max_length=180, default='A second opinion can make all the difference.')
	text = models.CharField(max_length=320, default='Tell us about your room, the work you love, and what you are looking for.')
	image = models.ImageField(upload_to='curator-advice/', blank=True)
	whatsapp_message = models.CharField(max_length=240, default='Hello, I would like some free art advice.')
	button_text = models.CharField(max_length=60, default='Talk to a Curator')
	is_active = models.BooleanField(default=True)

	def save(self, *args, **kwargs):
		optimize_uploaded_image(self, 'image')
		super().save(*args, **kwargs)

	def __str__(self):
		return self.heading