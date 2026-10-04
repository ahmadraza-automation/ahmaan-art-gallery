import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from core.images import optimize_uploaded_image


class CommissionRequest(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        REVIEWING = 'reviewing', 'Reviewing'
        QUOTED = 'quoted', 'Quoted'
        ACCEPTED = 'accepted', 'Accepted'
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'
        DECLINED = 'declined', 'Declined'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='commission_requests')
    customer_name = models.CharField(max_length=140)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=32)
    art_type = models.CharField(max_length=120)
    size = models.CharField(max_length=100)
    budget = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    deadline = models.DateField(null=True, blank=True)
    description = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    quote_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Commission request #{self.pk} - {self.customer_name}'


class CommissionReferenceImage(models.Model):
    request = models.ForeignKey(CommissionRequest, on_delete=models.CASCADE, related_name='reference_images')
    image = models.ImageField(upload_to='commission-references/')
    caption = models.CharField(max_length=180, blank=True)

    def save(self, *args, **kwargs):
        optimize_uploaded_image(self, 'image')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Reference image for request #{self.request_id}'
