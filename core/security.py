from functools import wraps
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

AUTH_ATTEMPT_LIMIT = 5
AUTH_ATTEMPT_PERIOD = 15 * 60
AUTH_LIMIT_MESSAGE = 'Too many attempts, try again in 15 minutes'


def _auth_cache_keys(request, identifier_field):
	client_ip = request.META.get(settings.RATE_LIMIT_CLIENT_IP_HEADER) if settings.RATE_LIMIT_CLIENT_IP_HEADER else None
	client_ip = client_ip or request.META.get('REMOTE_ADDR', 'unknown')
	path = request.path.rstrip('/')
	keys = [f'auth-attempt:ip:{sha256(f"{path}:{client_ip}".encode()).hexdigest()}']
	identifier = request.POST.get(identifier_field, '').strip().casefold()
	if identifier:
		keys.append(f'auth-attempt:identity:{sha256(f"{path}:{identifier}".encode()).hexdigest()}')
	return keys


def _increment_auth_counter(key):
	if not cache.add(key, 1, timeout=AUTH_ATTEMPT_PERIOD):
		try:
			cache.incr(key)
		except ValueError:
			cache.add(key, 1, timeout=AUTH_ATTEMPT_PERIOD)


def auth_attempt_limit(view_func=None, identifier_field='username', failed_only=False):
	def decorate(view):
		@wraps(view)
		def wrapped(request, *args, **kwargs):
			if request.method != 'POST':
				return view(request, *args, **kwargs)
			keys = _auth_cache_keys(request, identifier_field)
			if any((cache.get(key) or 0) >= AUTH_ATTEMPT_LIMIT for key in keys):
				return HttpResponse(AUTH_LIMIT_MESSAGE, status=429, content_type='text/plain; charset=utf-8')
			response = view(request, *args, **kwargs)
			if failed_only and 300 <= response.status_code < 400:
				cache.delete_many(keys)
			elif not failed_only or response.status_code < 300:
				for key in keys:
					_increment_auth_counter(key)
			return response
		return wrapped
	return decorate(view_func) if view_func else decorate


def rate_limit(max_requests, period=60):
	def decorator(view_func):
		@wraps(view_func)
		def wrapped(request, *args, **kwargs):
			if request.method != 'POST':
				return view_func(request, *args, **kwargs)
			client_ip = request.META.get(settings.RATE_LIMIT_CLIENT_IP_HEADER) if settings.RATE_LIMIT_CLIENT_IP_HEADER else None
			client_ip = client_ip or request.META.get('REMOTE_ADDR', 'unknown')
			key = sha256(f'{request.path}:{client_ip}'.encode()).hexdigest()
			limited_keys = getattr(request, '_rate_limit_keys', set())
			if key in limited_keys:
				return view_func(request, *args, **kwargs)
			limited_keys.add(key)
			request._rate_limit_keys = limited_keys
			cache_key = f'form-rate-limit:{key}'
			if cache.add(cache_key, 1, timeout=period):
				request_count = 1
			else:
				try:
					request_count = cache.incr(cache_key)
				except ValueError:
					cache.add(cache_key, 1, timeout=period)
					request_count = 1
			if request_count > max_requests:
				return HttpResponse('Too many attempts. Please try again shortly.', status=429)
			return view_func(request, *args, **kwargs)
		return wrapped
	return decorator