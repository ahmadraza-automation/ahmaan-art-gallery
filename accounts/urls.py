from django.urls import path

from accounts import views

app_name = 'accounts'

urlpatterns = [
	path('account/addresses/', views.saved_addresses, name='addresses'),
	path('account/addresses/<int:address_id>/delete/', views.delete_saved_address, name='delete_address'),
]
