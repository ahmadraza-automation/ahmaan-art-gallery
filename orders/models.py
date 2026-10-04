from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from uuid import uuid4

from catalog.models import Artwork, FrameOption, SizeOption
from core.images import optimize_uploaded_image


class Coupon(models.Model):
	code = models.CharField(max_length=40, unique=True)
	issued_to_email = models.EmailField(unique=True, null=True, blank=True)
	discount_percent = models.PositiveSmallIntegerField(default=0)
	discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	minimum_order = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	starts_at = models.DateTimeField(null=True, blank=True)
	expires_at = models.DateTimeField(null=True, blank=True)
	usage_limit = models.PositiveIntegerField(null=True, blank=True)
	uses = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	def save(self, *args, **kwargs):
		self.code = self.code.strip().upper()
		super().save(*args, **kwargs)

	@property
	def is_valid_now(self):
		now = timezone.now()
		return self.is_active and (self.starts_at is None or self.starts_at <= now) and (self.expires_at is None or self.expires_at >= now) and (self.usage_limit is None or self.uses < self.usage_limit)

	def __str__(self):
		return self.code


class Order(models.Model):
	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		CONFIRMED = 'confirmed', 'Confirmed'
		IN_PROGRESS = 'in_progress', 'In progress'
		PROCESSING = 'processing', 'Processing'
		SHIPPED = 'shipped', 'Shipped'
		DELIVERED = 'delivered', 'Delivered'
		COMPLETED = 'completed', 'Completed'
		CANCELLED = 'cancelled', 'Cancelled'

	class PaymentMethod(models.TextChoices):
		COD = 'cod', 'Cash on delivery'
		BANK_TRANSFER = 'bank_transfer', 'Bank transfer'
		JAZZCASH = 'jazzcash', 'JazzCash'
		EASYPAISA = 'easypaisa', 'Easypaisa'

	class PaymentStatus(models.TextChoices):
		UNPAID = 'unpaid', 'Unpaid'
		PROOF_SUBMITTED = 'proof_submitted', 'Proof submitted'
		PAID = 'paid', 'Paid'
		REFUNDED = 'refunded', 'Refunded'

	reference = models.CharField(max_length=24, unique=True, blank=True)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
	customer_name = models.CharField(max_length=140)
	customer_email = models.EmailField()
	customer_phone = models.CharField(max_length=32)
	delivery_address = models.TextField()
	city = models.CharField(max_length=100, blank=True)
	payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD)
	status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
	payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
	coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
	subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
	shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
	discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
	total = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
	customer_note = models.TextField(blank=True)
	certificate_id = models.UUIDField(default=uuid4, unique=True, editable=False)
	certificate_file = models.FileField(upload_to='certificates/', blank=True)
	tracking_code = models.CharField(max_length=80, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def save(self, *args, **kwargs):
		if not self.reference:
			self.reference = slugify(timezone.now().strftime('%y%m%d')) + '-' + uuid4().hex[:10].upper()
		super().save(*args, **kwargs)

	def __str__(self):
		return self.reference


class GiftCard(models.Model):
	AMOUNT_CHOICES = (
		(5000, 'PKR 5,000'),
		(10000, 'PKR 10,000'),
		(25000, 'PKR 25,000'),
		(50000, 'PKR 50,000'),
		(100000, 'PKR 100,000'),
	)

	amount = models.DecimalField(max_digits=12, decimal_places=2, choices=AMOUNT_CHOICES)
	code = models.CharField(max_length=40, unique=True, blank=True)
	recipient_name = models.CharField(max_length=120, blank=True)
	recipient_email = models.EmailField(blank=True)
	message = models.CharField(max_length=280, blank=True)
	is_active = models.BooleanField(default=False)
	is_redeemed = models.BooleanField(default=False)
	redeemed_at = models.DateTimeField(null=True, blank=True)
	redeemed_by_order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='gift_cards_redeemed')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def save(self, *args, **kwargs):
		if not self.code:
			self.code = uuid4().hex[:12].upper()
		else:
			self.code = self.code.strip().upper()
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.code} (PKR {self.amount})'


class GiftCardRedemption(models.Model):
	gift_card = models.ForeignKey(GiftCard, on_delete=models.PROTECT, related_name='redemptions')
	order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='gift_card_redemptions')
	amount_applied = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
	redeemed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-redeemed_at']

	def __str__(self):
		return f'{self.gift_card.code} redeemed on {self.order.reference}'


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	artwork = models.ForeignKey(Artwork, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
	title_at_order = models.CharField(max_length=180)
	unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
	quantity = models.PositiveSmallIntegerField(default=1)
	chosen_size = models.ForeignKey(SizeOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
	chosen_frame = models.ForeignKey(FrameOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
	chosen_canvas = models.ForeignKey('catalog.CanvasType', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
	custom_text = models.TextField(blank=True)

	@property
	def line_total(self):
		return self.unit_price * self.quantity

	def __str__(self):
		return f'{self.title_at_order} x {self.quantity}'


class PaymentProof(models.Model):
	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending review'
		APPROVED = 'approved', 'Approved'
		REJECTED = 'rejected', 'Rejected'

	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_proofs')
	image = models.ImageField(upload_to='payment-proofs/')
	amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
	reference_note = models.CharField(max_length=180, blank=True)
	status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
	created_at = models.DateTimeField(auto_now_add=True)

	def save(self, *args, **kwargs):
		optimize_uploaded_image(self, 'image')
		super().save(*args, **kwargs)

	def __str__(self):
		return f'Payment proof for {self.order}'