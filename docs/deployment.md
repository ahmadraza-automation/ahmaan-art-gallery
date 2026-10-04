# Production deployment

## Shared requirements

Use Python 3.10+, PostgreSQL, a unique `DJANGO_SECRET_KEY`, `DJANGO_SETTINGS_MODULE=config.settings_prod`, and `DJANGO_DEBUG=False`. Set these environment variables in the hosting provider, never commit production secrets:

- `DJANGO_SECRET_KEY`: generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
- `DJANGO_ALLOWED_HOSTS`: comma-separated exact hostnames, without schemes.
- `DJANGO_ADMIN_URL`: a secret path such as `gallery-control-<random>/`; include the trailing slash.
- `DATABASE_URL`: PostgreSQL URL supplied by the host.
- `PUBLIC_SITE_URL`: canonical HTTPS origin, for example `https://art.example.com`.
- `MEDIA_ROOT`: persistent writable directory for artist, artwork, commission, and payment-proof uploads.
- `RATE_LIMIT_CLIENT_IP_HEADER` (optional): a WSGI `META` key such as `HTTP_X_REAL_IP`, only when a trusted reverse proxy overwrites that header with the client IP. Leave unset otherwise; forwarded headers are not trusted by default.
- `WHATSAPP_NUMBER` and SMTP settings (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`) for production contact and order notifications.
- `ADMIN_EMAIL` for designer inquiry and artwork-offer notifications. Set `DEFAULT_FROM_EMAIL` to the sender address used by the gallery.
- `ADSENSE_ENABLED=True` and `ADSENSE_CLIENT_ID=ca-pub-...` only after AdSense setup is approved. Ads remain gated on the visitor accepting optional cookies; configure active AdSlot entries in admin for each placement. `/ads.txt` is served from the configured publisher ID.
- `DJANGO_SECURE_SSL_REDIRECT=True` when the trusted platform terminates TLS and sends `X-Forwarded-Proto: https`.

Production uses compressed manifest static files, secure session/CSRF cookies, HTTPS redirects, HSTS, nosniff, frame denial, and a PostgreSQL cache table for shared form/login rate limits. Create that table once per database with `python manage.py createcachetable django_cache` before starting web workers. Keep HSTS subdomain/preload settings disabled until every subdomain is HTTPS-ready.

Run migrations and collect static assets on every release:

```sh
python manage.py migrate
python manage.py createcachetable django_cache
python manage.py collectstatic --noinput
```

## Railway

1. Create a Railway project from the repository and add a PostgreSQL service. Attach its `DATABASE_URL` reference to the Django service.
2. Set the shared environment variables above, then set `DJANGO_SETTINGS_MODULE=config.settings_prod`, the exact Railway/custom host in `DJANGO_ALLOWED_HOSTS`, and the production HTTPS URL in `PUBLIC_SITE_URL`.
3. Add a persistent volume to the Django service mounted at `/app/media`; set `MEDIA_ROOT=/app/media`. Back up this volume. Railway volumes are tied to a service/region and are not shared object storage; keep a single web service unless media storage is migrated to shared object storage.
4. Set the release/pre-deploy command to `python manage.py migrate && python manage.py createcachetable django_cache && python manage.py collectstatic --noinput` (run cache-table creation only on initial provisioning if concurrent releases are possible).
5. Set the start command to `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --access-logfile -`.
6. Add the Railway domain or custom domain to `DJANGO_ALLOWED_HOSTS`, enable HTTPS, then verify `/`, `/sitemap.xml`, `/robots.txt`, the configured admin URL, and an uploaded-media URL.

## VPS: Gunicorn, Nginx, PostgreSQL, SSL

1. Provision a supported Linux server, PostgreSQL database/user, DNS A/AAAA records, and a dedicated unprivileged application user. Allow inbound ports 80/443; keep PostgreSQL private.
2. Clone the project to `/srv/ahmaan-art-gallery`, create a virtual environment, install `requirements.txt`, and create writable persistent directories `/srv/ahmaan/media` and `/srv/ahmaan/staticfiles`.
3. Configure a protected environment file for systemd with `DJANGO_SETTINGS_MODULE=config.settings_prod`, `DJANGO_SECRET_KEY`, exact `DJANGO_ALLOWED_HOSTS`, a non-default `DJANGO_ADMIN_URL`, PostgreSQL `DATABASE_URL`, `PUBLIC_SITE_URL=https://art.example.com`, `MEDIA_ROOT=/srv/ahmaan/media`, `DJANGO_DEBUG=False`, and email/WhatsApp credentials. Restrict its permissions to the service user.
4. Run `python manage.py migrate`, `python manage.py createcachetable django_cache`, and `python manage.py collectstatic --noinput` from the project directory using the service environment.
5. Run Gunicorn under systemd, bound to a Unix socket (for example `/run/ahmaan/gunicorn.sock`) with `config.wsgi:application`. Configure a systemd runtime directory owned by the application user and restart Gunicorn after releases.
6. Configure Nginx to proxy application requests to the socket and forward `Host`, `X-Real-IP $remote_addr`, `X-Forwarded-For`, and `X-Forwarded-Proto`. To use the actual client IP for rate limits, set `RATE_LIMIT_CLIENT_IP_HEADER=HTTP_X_REAL_IP`; Nginx must overwrite this header, not pass through a client-supplied value. Serve `/static/` from `STATIC_ROOT` and `/media/` from the persistent `MEDIA_ROOT`; do not execute uploaded files. Set reasonable request-body limits for commission references and payment proofs.
7. Obtain and renew a certificate with Certbot for the domain, redirect HTTP to HTTPS, then keep `DJANGO_SECURE_SSL_REDIRECT=True`. The existing trusted proxy header is configured for `X-Forwarded-Proto`; do not expose the application directly to untrusted clients that can spoof that header.
8. Back up PostgreSQL and media independently, test restoration, monitor disk space/logs, and keep the OS, Python dependencies, and TLS configuration patched.

For multiple app instances or regions, migrate local media to an S3-compatible private bucket with controlled public/image delivery, and replace the database cache with a shared Redis cache. The repository currently supports persistent filesystem media and PostgreSQL-backed cache; object-storage/Redis adapters are not included.
