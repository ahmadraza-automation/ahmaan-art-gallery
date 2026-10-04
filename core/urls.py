from django.urls import path

from core import views

app_name = 'core'

urlpatterns = [
	path('journal/', views.journal_index, name='journal_index'),
	path('journal/<slug:slug>/', views.journal_detail, name='journal_detail'),
	path('for-designers/', views.for_designers, name='for_designers'),
	path('shipping-payments/', views.shipping_payments, name='shipping_payments'),
	path('cookie-policy/', views.cookie_policy, name='cookie_policy'),
	path('faq/', views.faq_page, name='faq'),
	path('faqs/', views.faq_page, name='faqs'),
	path('quiz/', views.art_match, name='quiz'),
	path('art-match/', views.art_match, name='art_match'),
	path('shipping/', views.shipping_page, name='shipping'),
	path('returns/', views.returns_page, name='returns'),
	path('privacy/', views.privacy_page, name='privacy'),
	path('terms/', views.terms_page, name='terms'),
	path('newsletter/', views.newsletter_signup, name='newsletter_signup'),
]