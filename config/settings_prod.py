from django.core.exceptions import ImproperlyConfigured

from .settings_security import validate_production_values

from .settings_base import *

DEBUG = False
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()]
validate_production_values(SECRET_KEY, ALLOWED_HOSTS)
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
	raise ImproperlyConfigured('Set DATABASE_URL to a PostgreSQL connection for production.')
if not PUBLIC_SITE_URL.startswith('https://'):
	raise ImproperlyConfigured('Set PUBLIC_SITE_URL to the canonical HTTPS origin in production.')
STORAGES['staticfiles'] = {
	'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
}
CACHES = {
	'default': {
		'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
		'LOCATION': os.environ.get('DJANGO_CACHE_TABLE', 'django_cache'),
	},
}
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '3600'))  # Raise after confirming all subdomains support HTTPS.
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'
proxy_ssl_header = os.environ.get('DJANGO_SECURE_PROXY_SSL_HEADER', 'HTTP_X_FORWARDED_PROTO:https').strip()
if proxy_ssl_header:
	proxy_header, separator, proxy_value = proxy_ssl_header.partition(':')
	if not separator or not proxy_header or not proxy_value:
		raise ImproperlyConfigured('DJANGO_SECURE_PROXY_SSL_HEADER must use HEADER_NAME:VALUE or be empty.')
	SECURE_PROXY_SSL_HEADER = (proxy_header, proxy_value)
else:
	SECURE_PROXY_SSL_HEADER = None

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
# Content-Security-Policy will be added later in report-only mode.