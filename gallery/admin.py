from django.contrib import admin
from django.utils.html import format_html

from core.admin_utils import ExportModelAdmin, SingletonModelAdmin
from .models import Artwork, ArtworkCategory, ContactInquiry, GalleryProfile, LegacyWishlist, Order

admin.site.site_header = 'Ahmaan Art Gallery Administration'
admin.site.site_title = 'Ahmaan Gallery Admin'
admin.site.index_title = 'Gallery management'


@admin.register(Artwork)
class ArtworkAdmin(ExportModelAdmin):
	list_display = ('title', 'artist', 'category', 'availability_badge', 'is_featured', 'is_popular')
	list_filter = ('category', 'is_available', 'is_featured', 'is_popular')
	search_fields = ('title', 'artist', 'description')
	prepopulated_fields = {'slug': ('title',)}
	list_select_related = ('category',)

	@admin.display(description='Availability', ordering='is_available')
	def availability_badge(self, obj):
		label = 'Available' if obj.is_available else 'Sold'
		color = '#16794b' if obj.is_available else '#666666'
		return format_html('<strong style="color:{}">{}</strong>', color, label)


@admin.register(ArtworkCategory)
class ArtworkCategoryAdmin(ExportModelAdmin):
	list_display = ('name', 'slug', 'sort_order', 'is_active')
	list_editable = ('sort_order', 'is_active')
	prepopulated_fields = {'slug': ('name',)}
	search_fields = ('name', 'slug')


@admin.register(LegacyWishlist)
class LegacyWishlistAdmin(ExportModelAdmin):
	list_display = ('user', 'artwork', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('user__username', 'user__email', 'artwork__title', 'artwork__artist')
	list_select_related = ('user', 'artwork')


@admin.register(GalleryProfile)
class GalleryProfileAdmin(SingletonModelAdmin):
	list_display = ('artist_name', 'updated_at')
	readonly_fields = ('updated_at',)


@admin.register(ContactInquiry)
class ContactInquiryAdmin(ExportModelAdmin):
	list_display = ('subject', 'name', 'email', 'submitted_at')
	search_fields = ('name', 'email', 'subject', 'message')
	readonly_fields = ('name', 'email', 'subject', 'message', 'submitted_at')


@admin.register(Order)
class OrderAdmin(ExportModelAdmin):
	list_display = ('id', 'order_type', 'requested_title', 'customer_name', 'quantity', 'customer_phone', 'payment_method', 'status', 'created_at')
	list_filter = ('order_type', 'status', 'art_category', 'size', 'frame', 'created_at')
	search_fields = ('customer_name', 'customer_email', 'customer_phone', 'requested_title')
	readonly_fields = ('created_at',)
