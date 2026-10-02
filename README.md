# Ahmaan Art Gallery

Ahmaan Art Gallery is a Django art shop for the Pakistani market. The existing `gallery` app continues to run the storefront; the Part 1 domain foundation adds separate `catalog`, `orders`, `commissions`, `accounts`, and `core` apps without discarding existing storefront data. Prices are stored as decimal PKR amounts.

## Local setup

Use Python 3.10 or newer. From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_gallery
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`; the admin is at `/admin/`. Local development uses SQLite by default. Configure `WHATSAPP_NUMBER` in `.env` using the international number without a leading `+`.

## Data and uploads

`python manage.py seed_gallery` creates or updates five categories, four collections, three artists, and twelve sample catalog artworks. The seed command can be run repeatedly. The current live storefront also has its own legacy sample content; this command seeds the new `catalog` models and does not replace the storefront's existing records.

Uploaded model images are converted to WebP and stored with 2400, 1200, 600, and 320 pixel wide variants under `media/`. Variant processing keeps aspect ratio and does not enlarge images smaller than a requested size. Store media on persistent storage in production and configure backups/access controls for customer uploads.

The new apps expose admin screens for all models. List pages include CSV export; artwork and commission editors have image inlines. Site settings can be edited once as a singleton.

The home page uses catalog artworks, collections, hero slides, artist profiles, Instagram images, testimonials, and journal posts managed in the admin. Add video to a hero slide with its `HeroSlideVideo` inline; use a directly playable MP4/WebM URL and keep the slide image as its poster. `SiteSettings` controls the announcement copy, complimentary-shipping threshold, contact details, and social links. The first-visit popup is edited through `WelcomeOffer`. Newsletter submissions are stored in `NewsletterSubscriber`.

The design system includes a persisted light/dark toggle, responsive collection navigation, reduced-motion-aware reveals, and a local wishlist preview. Quick-add and wishlist actions are intentionally presentation-only in this part; order/cart integration is reserved for the later checkout work.

## PostgreSQL production

Set these environment values in the deployment environment (do not commit secrets): `DJANGO_SETTINGS_MODULE=config.settings_prod`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `DATABASE_URL` with a PostgreSQL URL such as `postgres://user:password@host:5432/database`. Production settings require PostgreSQL, enable secure cookies and HTTPS redirects, and use WhiteNoise's compressed manifest static storage.

Then run:

```powershell
python manage.py migrate
python manage.py collectstatic --noinput
```

Set `DJANGO_SECURE_SSL_REDIRECT=False` only when HTTPS is terminated by a trusted proxy that already redirects HTTP. Keep `DEBUG` off in production.
