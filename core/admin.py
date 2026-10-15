from django.contrib import admin
from django import forms
from django.db import models

from core.admin_utils import ExportModelAdmin, SingletonModelAdmin
from .models import (
	AdSlot, ArtMatchOption, ArtMatchQuestion, Banner, BrandStory, CityDeliveryTime,
	ConsultationRequest, CuratorAdviceBanner, CustomerReview, DesignerInquiry, FAQ,
	HeroSlide, HeroSlideVideo, InstagramImage, JournalPost,
	NewsletterSubscriber, PressMention, SiteSettings, Testimonial, TrustFeature, WelcomeOffer,
	ShippingPaymentContent,
)


class HeroSlideVideoInline(admin.StackedInline):
	model = HeroSlideVideo
	extra = 0


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonModelAdmin):
	list_display = ('gallery_name', 'whatsapp_number', 'updated_at')
	search_fields = ('gallery_name', 'announcement_bar_text', 'address', 'whatsapp_number')
	readonly_fields = ('updated_at',)
	formfield_overrides = {
		models.TextField: {'widget': forms.Textarea(attrs={'rows': 4})},
	}
	fieldsets = (
		('Gallery identity', {
			'fields': ('gallery_name', 'tagline', 'logo', 'announcement_bar_text', 'announcement_bar_enabled'),
			'help_text': 'Set the gallery name, tagline, logo, and announcement bar.'
		}),
		('Contact', {
			'fields': ('phone', 'whatsapp_number', 'address', 'opening_hours', 'contact_location', 'contact_hours', 'contact_intro', 'support_reply_hours', 'google_maps_url'),
			'help_text': 'Set contact details and the contact page information.'
		}),
		('Social links', {
			'fields': ('instagram_url', 'facebook_url', 'pinterest_url', 'youtube_url', 'tiktok_url', 'other_social_links'),
			'help_text': 'Add social media links shown in the site footer.'
		}),
		('Offer tab', {
			'fields': ('offer_tab_label', 'offer_dialog_heading'),
			'help_text': 'Change the newsletter offer tab and dialog heading.'
		}),
		('Newsletter and support', {
			'fields': ('newsletter_sender_name', 'newsletter_sender_email', 'footer_newsletter_heading', 'footer_newsletter_text', 'footer_email'),
			'help_text': 'Set the newsletter sender and support reply information.'
		}),
		('Shipping and payment', {
			'fields': ('flat_shipping_rate', 'free_shipping_threshold', 'minimum_delivery_days', 'maximum_delivery_days', 'payment_badge_cod', 'payment_badge_bank_transfer', 'payment_badge_jazzcash', 'payment_badge_easypaisa', 'bank_name', 'bank_account_title', 'bank_account_number', 'bank_iban', 'jazzcash_account_title', 'jazzcash_number', 'easypaisa_account_title', 'easypaisa_number', 'minimum_offer_percent', 'payment_instructions'),
			'help_text': 'Manage shipping, payments, and offer limits.'
		}),
		('About page', {
			'fields': ('about_description', 'mission_text', 'process_text', 'promise_text'),
			'help_text': 'Edit the gallery story and about-page sections.'
		}),
		('Policies', {
			'fields': ('shipping_policy', 'returns_policy', 'cancellation_policy', 'damage_in_transit_policy', 'authenticity_policy', 'privacy_policy', 'terms_conditions', 'cookie_policy', 'faq_intro'),
			'help_text': 'Edit the copy shown on policy and FAQ pages.'
		}),
		('Shipping and delivery', {
			'fields': ('packaging_text', 'shipping_partner', 'delivery_headline', 'delivery_estimate_text'),
			'help_text': 'Set packaging, carrier, and delivery information.'
		}),
		('Payments', {
			'fields': ('cod_description', 'jazzcash_description', 'easypaisa_description'),
			'help_text': 'Describe the available payment methods.'
		}),
		('Homepage text', {
			'fields': ('home_price_section_title', 'home_accessories_title', 'home_accessories_text'),
			'help_text': 'Edit headings and copy shown on the homepage.'
		}),
		('Commission service', {
			'fields': ('commission_minimum_price', 'commission_completion_time', 'commission_advance_percent'),
			'help_text': 'Set optional price, timing, and advance details.'
		}),
	)


@admin.register(HeroSlide)
class HeroSlideAdmin(ExportModelAdmin):
	list_display = ('title', 'order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('title', 'subtitle')
	inlines = (HeroSlideVideoInline,)


@admin.register(Banner)
class BannerAdmin(ExportModelAdmin):
	list_display = ('title', 'order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('title',)


@admin.register(InstagramImage)
class InstagramImageAdmin(ExportModelAdmin):
	list_display = ('caption', 'order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('caption',)


@admin.register(Testimonial)
class TestimonialAdmin(ExportModelAdmin):
	list_display = ('name', 'location', 'rating', 'is_verified', 'is_published', 'order')
	list_filter = ('is_verified', 'is_published', 'rating')
	search_fields = ('name', 'location', 'quote')


@admin.register(FAQ)
class FAQAdmin(ExportModelAdmin):
	list_display = ('question', 'category', 'order', 'is_published')
	list_filter = ('category', 'is_published')
	search_fields = ('question', 'answer')


@admin.register(CustomerReview)
class CustomerReviewAdmin(ExportModelAdmin):
	list_display = ('title', 'name', 'city', 'rating', 'is_verified', 'is_approved', 'created_at')
	list_filter = ('is_approved', 'is_verified', 'rating', 'created_at')
	search_fields = ('name', 'city', 'title', 'text')
	readonly_fields = ('created_at',)


@admin.register(TrustFeature)
class TrustFeatureAdmin(ExportModelAdmin):
	list_display = ('title', 'icon', 'order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('title', 'description')


@admin.register(BrandStory)
class BrandStoryAdmin(ExportModelAdmin):
	list_display = ('heading', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('heading', 'story')


@admin.register(PressMention)
class PressMentionAdmin(ExportModelAdmin):
	list_display = ('publication', 'order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('publication',)


@admin.register(WelcomeOffer)
class WelcomeOfferAdmin(ExportModelAdmin):
	list_display = ('title', 'offer_code', 'is_active', 'updated_at')
	list_filter = ('is_active', 'updated_at')
	search_fields = ('title', 'message', 'offer_code')
	readonly_fields = ('updated_at',)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ExportModelAdmin):
	list_display = ('email', 'is_active', 'subscribed_at')
	list_filter = ('is_active', 'subscribed_at')
	search_fields = ('email',)
	readonly_fields = ('email', 'subscribed_at')


@admin.register(JournalPost)
class JournalPostAdmin(ExportModelAdmin):
	list_display = ('title', 'category', 'author', 'published_at', 'is_published')
	list_filter = ('category', 'is_published', 'published_at')
	search_fields = ('title', 'slug', 'excerpt', 'body', 'author')
	prepopulated_fields = {'slug': ('title',)}
	date_hierarchy = 'published_at'


@admin.register(DesignerInquiry)
class DesignerInquiryAdmin(ExportModelAdmin):
	list_display = ('name', 'company', 'email', 'project_type', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('name', 'company', 'email', 'phone', 'project_type', 'message')
	readonly_fields = ('created_at',)


@admin.register(ShippingPaymentContent)
class ShippingPaymentContentAdmin(SingletonModelAdmin):
	readonly_fields = ('updated_at',)


@admin.register(CityDeliveryTime)
class CityDeliveryTimeAdmin(ExportModelAdmin):
	list_display = ('city', 'minimum_days', 'maximum_days', 'order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('city',)


@admin.register(AdSlot)
class AdSlotAdmin(ExportModelAdmin):
	list_display = ('name', 'key', 'slot_id', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('name', 'key', 'slot_id')


class ArtMatchOptionInline(admin.TabularInline):
	model = ArtMatchOption
	extra = 0


@admin.register(ArtMatchQuestion)
class ArtMatchQuestionAdmin(ExportModelAdmin):
	list_display = ('prompt', 'key', 'order', 'is_active')
	list_filter = ('is_active', 'key')
	search_fields = ('prompt',)
	inlines = (ArtMatchOptionInline,)


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(ExportModelAdmin):
	list_display = ('name', 'email', 'phone', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('name', 'email', 'phone', 'message')
	readonly_fields = ('created_at',)


@admin.register(CuratorAdviceBanner)
class CuratorAdviceBannerAdmin(ExportModelAdmin):
	list_display = ('heading', 'button_text', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('heading', 'text', 'whatsapp_message')