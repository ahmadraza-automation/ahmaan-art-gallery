# Ahmaan Art Gallery

**Independent Art Platform for Pakistan**  
Original artworks, commissions, and curated collections — built for collectors across Pakistan with local payment methods and nationwide delivery.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2-green)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-Private-red)]()

---

## Overview

Ahmaan Art Gallery is a full-featured Django e-commerce platform specialized for the Pakistani art market. It combines a modern storefront with powerful admin tools for managing original artworks, limited editions, commissions, gift cards, and order fulfillment.

### Key Highlights
- Designed for **PKR pricing** and local payment methods (COD, Bank Transfer, JazzCash, Easypaisa)
- Unique **one-of-a-kind artwork reservation** system (24-hour hold)
- Automatic **Certificate of Authenticity** generation with QR verification
- Complete order lifecycle with tracking, payment proof review, and WhatsApp integration
- Light/Dark mode, responsive design, and SEO-ready pages

---

## Features

### Storefront & Catalog
- Beautiful collection-based browsing (Quiet Landscapes, Letters of Light, Everyday Reverie, Portrait Studies)
- Artist profiles with interviews and city information
- Advanced filtering by category, style, subject, price range, and room
- Artwork detail pages with size, frame, and canvas options
- Session-based cart + wishlist (works for guests and logged-in users)
- Hero slides with optional video support
- Journal / blog section
- Newsletter subscription & welcome offers

### Orders & Checkout
- Multi-item cart supporting both catalog and legacy artworks
- Coupons & Gift Cards (fixed PKR denominations)
- Payment methods: Cash on Delivery, Bank Transfer, JazzCash, Easypaisa
- Payment proof upload & admin approval workflow
- Automatic reservation of unique artworks during checkout
- Order confirmation with WhatsApp deep-link
- Order tracking by reference + phone number
- Order history for authenticated users

### Certificates & Trust
- Auto-generated PDF Certificate of Authenticity
- Unique certificate ID + QR code for public verification
- Public verification page (`/verify/<certificate_id>/`)

### Commissions
- Custom commission request flow
- Admin management of commission status and images

### Accounts
- User profiles with saved addresses
- Order history and saved preferences

### Admin & Operations
- Full Django admin with CSV export on key models
- Sales analytics on order list page
- Site settings singleton (shipping rates, payment details, announcement bar, social links)
- Image optimization (WebP + multiple size variants)
- Seed command for demo data

---

## Tech Stack

| Layer              | Technology                          |
|--------------------|-------------------------------------|
| Backend            | Django 5.2                          |
| Database           | SQLite (dev) / PostgreSQL (prod)    |
| Image Processing   | Pillow + custom WebP variants       |
| PDF Certificates   | ReportLab + QRCode                  |
| Static Files       | WhiteNoise                          |
| Payments           | Custom providers (COD, Bank, JazzCash, Easypaisa) |
| Frontend           | Custom CSS + light/dark mode        |

---

## Screenshots

### Homepage Hero
![Homepage Hero](docs/screenshots/homepage-hero.jpeg)

### Collections
![Collections](docs/screenshots/collections.jpeg)

### How It Works
![How It Works](docs/screenshots/homepage-how-it-works.jpeg)

---

## Project Structure

```
ahmaan-art-gallery/
├── accounts/          # User profiles & saved addresses
├── catalog/           # Artworks, artists, collections, categories
├── commissions/       # Custom commission requests
├── config/            # Settings (dev/prod), URLs, ASGI/WSGI
├── core/              # Site settings, journal, testimonials, FAQs, trust features
├── gallery/           # Legacy storefront (still active)
├── orders/            # Checkout, payments, certificates, tracking
├── docs/
│   └── screenshots/   # Project screenshots
├── manage.py
├── requirements.txt
└── .env.example
```

---

## Local Setup

**Requirements:** Python 3.10+

```powershell
# 1. Clone & enter project
git clone https://github.com/ahmadraza-automation/ahmaan-art-gallery.git
cd ahmaan-art-gallery

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Environment
Copy-Item .env.example .env
# Edit .env and set WHATSAPP_NUMBER, ADMIN_EMAIL, etc.

# 5. Database & seed data
python manage.py migrate
python manage.py seed_gallery
python manage.py createsuperuser

# 6. Run
python manage.py runserver
```

Open:
- Storefront → http://127.0.0.1:8000/
- Admin → http://127.0.0.1:8000/admin/

---

## Production Deployment

Set these environment variables (never commit secrets):

```
DJANGO_SETTINGS_MODULE=config.settings_prod
DJANGO_SECRET_KEY=your-strong-secret
DJANGO_ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgres://user:password@host:5432/dbname
```

Then:

```powershell
python manage.py migrate
python manage.py collectstatic --noinput
```

See `docs/deployment.md` for Railway / VPS guides (Gunicorn + Nginx + HTTPS).

---

## Running Tests

```powershell
python manage.py test catalog.tests core.tests gallery.tests
python manage.py check
python manage.py makemigrations --check --dry-run
```

---

## License

Private project — All rights reserved.

---

**Built with care for the Pakistani art community.**  
Developed by [Ahmad Raza](https://github.com/ahmadraza-automation)
