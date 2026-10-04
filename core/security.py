from functools import wraps
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


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