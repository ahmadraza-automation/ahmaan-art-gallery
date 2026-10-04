from django.core.exceptions import ImproperlyConfigured

from .settings_base import *

DEBUG = False
if len(SECRET_KEY) < 50 or SECRET_KEY == 'local-development-key-not-for-production':
	raise ImproperlyConfigured('Set DJANGO_SECRET_KEY to a random value at least 50 characters long.')
if not ALLOWED_HOSTS:
	raise ImproperlyConfigured('Set DJANGO_ALLOWED_HOSTS for production.')
if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
	raise ImproperlyConfigured('Set DATABASE_URL to a PostgreSQL connection for production.')
if not PUBLIC_SITE_URL.startswith('https://'):
	raise ImproperlyConfigured('Set PUBLIC_SITE_URL to the canonical HTTPS origin in production.')
if DJANGO_ADMIN_URL == 'admin/':
	raise ImproperlyConfigured('Set DJANGO_ADMIN_URL to a non-default admin path in production.')

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
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'