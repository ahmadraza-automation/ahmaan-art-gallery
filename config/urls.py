"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.contrib.sitemaps.views import sitemap

from core.sitemaps import sitemaps
from core.security import auth_attempt_limit
from core.views import ads_txt, robots_txt

admin.site.login = auth_attempt_limit(admin.site.login, identifier_field='username', failed_only=True)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('ads.txt', ads_txt, name='ads_txt'),
    path('', include('gallery.urls')),
    path('', include('core.urls')),
    path('', include('orders.urls')),
    path('', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
