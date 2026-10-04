from django.conf import settings
from django.db import models


class AccountProfile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='gallery_profile')
	phone = models.CharField(max_length=32, blank=True)
	address = models.TextField(blank=True)
	city = models.CharField(max_length=100, blank=True)
	marketing_opt_in = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f'Profile for {self.user}'


class SavedAddress(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_gallery_addresses')
	label = models.CharField(max_length=60, default='Home')
	recipient_name = models.CharField(max_length=140)
	phone = models.CharField(max_length=32)
	address_line1 = models.CharField(max_length=220)
	address_line2 = models.CharField(max_length=220, blank=True)
	city = models.CharField(max_length=100)
	postal_code = models.CharField(max_length=20, blank=True)
	is_default = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-is_default', 'label', 'pk']

	def save(self, *args, **kwargs):
		if self.is_default:
			SavedAddress.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
		super().save(*args, **kwargs)

	def __str__(self):
		return f'{self.label} - {self.city}'