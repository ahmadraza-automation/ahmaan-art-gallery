from pathlib import Path
import os
from urllib.parse import parse_qsl, unquote, urlsplit

BASE_DIR = Path(__file__).resolve().parent.parent

env_file = BASE_DIR / '.env'
if env_file.exists():
	for line in env_file.read_text(encoding='utf-8').splitlines():
		line = line.strip()
		if line and not line.startswith('#') and '=' in line:
			key, value = line.split('=', 1)
			os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def env_bool(name, default=False):
	return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'local-development-key-not-for-production')
DEBUG = env_bool('DJANGO_DEBUG', True)
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()]

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'django.contrib.sitemaps',
	'gallery',
	'catalog',
	'orders',
	'commissions',
	'accounts',
	'core',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
	'BACKEND': 'django.template.backends.django.DjangoTemplates',
	'DIRS': [BASE_DIR / 'templates'],
	'APP_DIRS': True,
	'OPTIONS': {'context_processors': [
		'django.template.context_processors.request',
		'django.contrib.auth.context_processors.auth',
		'django.contrib.messages.context_processors.messages',
		'gallery.context_processors.storefront',
	]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

database_url = os.environ.get('DATABASE_URL', '').strip()
if database_url:
	parsed_database_url = urlsplit(database_url)
	if parsed_database_url.scheme not in ('postgres', 'postgresql', 'postgresql+psycopg'):
		raise ValueError('DATABASE_URL must use PostgreSQL (or leave it unset for SQLite).')
	DATABASES = {'default': {
		'ENGINE': 'django.db.backends.postgresql',
		'NAME': unquote(parsed_database_url.path.lstrip('/')),
		'USER': unquote(parsed_database_url.username or ''),
		'PASSWORD': unquote(parsed_database_url.password or ''),
		'HOST': parsed_database_url.hostname or '',
		'PORT': parsed_database_url.port or '',
		'OPTIONS': dict(parse_qsl(parsed_database_url.query)),
	}}
else:
	DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [
	{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
	{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
	{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
	{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))
STORAGES = {
	'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
	'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = 'gallery:home'
LOGOUT_REDIRECT_URL = 'gallery:home'
WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', os.environ.get('DEFAULT_FROM_EMAIL', 'hello@ahmaanartgallery.pk'))
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'hello@ahmaanartgallery.pk')
ADSENSE_ENABLED = env_bool('ADSENSE_ENABLED', False)
ADSENSE_CLIENT_ID = os.environ.get('ADSENSE_CLIENT_ID', '').strip()
PUBLIC_SITE_URL = os.environ.get('PUBLIC_SITE_URL', 'http://127.0.0.1:8000')
DJANGO_ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'admin/').strip('/') + '/'
RATE_LIMIT_CLIENT_IP_HEADER = os.environ.get('RATE_LIMIT_CLIENT_IP_HEADER', '').strip()
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')