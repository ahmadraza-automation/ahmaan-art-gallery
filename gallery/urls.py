from django.urls import path
from django.contrib.auth import views as auth_views

from core.security import rate_limit
from . import catalog_views, views

app_name = 'gallery'

urlpatterns = [
    path('', views.home, name='home'),
    path('reviews/submit/', views.collector_review_submit, name='review_submit'),
    path('shop/', catalog_views.shop, name='shop'),
    path('search/', catalog_views.search, name='artwork_search'),
    path('collections/', catalog_views.collections_index, name='collections'),
    path('collections/<slug:slug>/', catalog_views.collection_detail, name='collection_detail'),
    path('rooms/<slug:slug>/', catalog_views.room_detail, name='room_detail'),
    path('new-arrivals/', catalog_views.new_arrivals, name='new_arrivals'),
    path('artists/', catalog_views.artists_index, name='artists'),
    path('artists/<slug:slug>/', catalog_views.artist_detail, name='artist_detail'),
    path('archive/', catalog_views.archive, name='archive'),
    path('wishlist/', catalog_views.wishlist_page, name='wishlist'),
    path('wishlist/toggle/<int:artwork_id>/', catalog_views.wishlist_toggle, name='wishlist_toggle'),
    path('wishlist/legacy-toggle/<int:artwork_id>/', catalog_views.legacy_wishlist_toggle, name='legacy_wishlist_toggle'),
    path('compare/', catalog_views.compare_page, name='compare'),
    path('compare/toggle/<int:artwork_id>/', catalog_views.compare_toggle, name='compare_toggle'),
    path('compare/legacy-toggle/<int:artwork_id>/', catalog_views.legacy_compare_toggle, name='legacy_compare_toggle'),
    path('sets/<slug:slug>/', catalog_views.bundle_detail, name='bundle_detail'),
    path('artwork/<slug:slug>/', catalog_views.artwork_detail, name='artwork_detail'),
    path('artwork/<slug:slug>/offer/', catalog_views.submit_offer, name='catalog_offer'),
    path('artwork/<slug:slug>/add/', catalog_views.add_catalog_item, name='catalog_add'),
    path('catalog-cart/remove/<str:line_id>/', catalog_views.remove_catalog_item, name='catalog_cart_remove'),
    path('catalog-cart/update/<str:line_id>/', catalog_views.update_catalog_item, name='catalog_cart_update'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/update/<str:line_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<str:line_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/complete/<uuid:reference>/', views.checkout_complete, name='checkout_complete'),
    path('commission/', views.commission, name='commission'),
    path('account/', views.profile, name='profile'),
    path('order/<int:order_id>/complete/', views.order_complete, name='order_complete'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('accounts/signup/', views.signup, name='signup'),
    path('accounts/login/', rate_limit(5, period=300)(catalog_views.GalleryLoginView.as_view(template_name='registration/login.html')), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]