from django.core.exceptions import ImproperlyConfigured


def validate_production_values(secret_key, allowed_hosts):
	if not secret_key or len(secret_key) < 50 or secret_key.lower().startswith('django-insecure-'):
		raise ImproperlyConfigured('Set DJANGO_SECRET_KEY to a random value at least 50 characters long.')
	if not allowed_hosts or any('*' in host for host in allowed_hosts):
		raise ImproperlyConfigured('Set DJANGO_ALLOWED_HOSTS to exact hostnames; wildcard hosts are not allowed.')
