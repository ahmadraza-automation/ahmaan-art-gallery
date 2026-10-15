from django.urls import path

from orders import views

app_name = 'orders'

urlpatterns = [
	path('gift-cards/', views.gift_cards, name='gift_cards'),
	path('checkout/', views.checkout, name='checkout'),
	path('checkout/order/<str:reference>/', views.confirmation, name='confirmation'),
	path('orders/track/', views.track_order, name='track'),
	path('orders/history/', views.order_history, name='history'),
	path('verify/<str:certificate_id>/', views.verify_certificate, name='verify_certificate'),
	path('certificates/<uuid:certificate_id>/download/', views.download_certificate, name='certificate_download'),
]
