from django.contrib import admin

from core.admin_utils import ExportModelAdmin
from .models import (
	Artist, Artwork, ArtworkBundle, ArtworkBundleItem, ArtworkImage, ArtworkOffer, CanvasType,
	Category, Collection, FrameOption, NotifyRequest, PriceRange, Review, Room,
	SizeOption, Wishlist,
)


class ArtworkImageInline(admin.TabularInline):
	model = ArtworkImage
	extra = 0
	fields = ('image', 'alt_text', 'order')


class ArtworkBundleItemInline(admin.TabularInline):
	model = ArtworkBundleItem
	extra = 2
	max_num = 3
	autocomplete_fields = ('artwork',)


@admin.register(Artwork)
class ArtworkAdmin(ExportModelAdmin):
	list_display = ('title', 'artist', 'category', 'base_price', 'is_one_of_a_kind', 'is_featured', 'is_best_seller')
	list_filter = ('status', 'category', 'artist', 'is_one_of_a_kind', 'is_limited_edition', 'is_featured', 'is_best_seller')
	search_fields = ('title', 'slug', 'mood_tagline', 'story', 'artist__name', 'category__name')
	prepopulated_fields = {'slug': ('title',)}
	filter_horizontal = ('collections', 'rooms')
	list_select_related = ('artist', 'category')
	inlines = (ArtworkImageInline,)


@admin.register(Artist)
class ArtistAdmin(ExportModelAdmin):
	list_display = ('name', 'city', 'specialty', 'slug')
	search_fields = ('name', 'slug', 'city', 'specialty', 'bio')
	prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(ExportModelAdmin):
	list_display = ('name', 'slug', 'order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('name', 'slug', 'description')
	prepopulated_fields = {'slug': ('name',)}


@admin.register(Collection)
class CollectionAdmin(ExportModelAdmin):
	list_display = ('name', 'is_featured', 'order', 'slug')
	list_filter = ('is_featured',)
	search_fields = ('name', 'slug', 'short_description')
	prepopulated_fields = {'slug': ('name',)}


@admin.register(Room)
class RoomAdmin(ExportModelAdmin):
	list_display = ('name', 'slug', 'order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('name', 'slug', 'short_description')
	prepopulated_fields = {'slug': ('name',)}


@admin.register(PriceRange)
class PriceRangeAdmin(ExportModelAdmin):
	list_display = ('label', 'minimum_price', 'maximum_price', 'order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('label',)


@admin.register(ArtworkImage)
class ArtworkImageAdmin(ExportModelAdmin):
	list_display = ('artwork', 'alt_text', 'order')
	search_fields = ('artwork__title', 'alt_text')
	list_select_related = ('artwork',)


@admin.register(SizeOption)
class SizeOptionAdmin(ExportModelAdmin):
	list_display = ('name', 'width', 'height', 'price_modifier', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('name',)


@admin.register(FrameOption)
class FrameOptionAdmin(ExportModelAdmin):
	list_display = ('name', 'price_modifier', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('name',)


@admin.register(CanvasType)
class CanvasTypeAdmin(ExportModelAdmin):
	list_display = ('name', 'price_modifier', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('name', 'description')


@admin.register(Review)
class ReviewAdmin(ExportModelAdmin):
	list_display = ('artwork', 'name', 'rating', 'is_approved', 'created_at')
	list_filter = ('is_approved', 'rating', 'created_at')
	search_fields = ('artwork__title', 'name', 'text')
	list_select_related = ('artwork',)


@admin.register(Wishlist)
class WishlistAdmin(ExportModelAdmin):
	list_display = ('user', 'artwork', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('user__username', 'user__email', 'artwork__title')
	list_select_related = ('user', 'artwork')


@admin.register(NotifyRequest)
class NotifyRequestAdmin(ExportModelAdmin):
	list_display = ('channel', 'email', 'whatsapp', 'artwork', 'category', 'is_notified', 'created_at')
	list_filter = ('channel', 'is_notified', 'created_at')
	search_fields = ('email', 'whatsapp', 'artwork__title', 'category__name')
	list_select_related = ('artwork', 'category')


@admin.register(ArtworkBundle)
class ArtworkBundleAdmin(ExportModelAdmin):
	list_display = ('name', 'bundle_price', 'is_featured', 'is_active', 'created_at')
	list_filter = ('is_active', 'is_featured', 'created_at')
	search_fields = ('name', 'slug', 'short_description')
	prepopulated_fields = {'slug': ('name',)}
	inlines = (ArtworkBundleItemInline,)

	def save_related(self, request, form, formsets, change):
		super().save_related(request, form, formsets, change)
		form.instance.full_clean()


@admin.register(ArtworkBundleItem)
class ArtworkBundleItemAdmin(ExportModelAdmin):
	list_display = ('bundle', 'artwork', 'order')
	search_fields = ('bundle__name', 'artwork__title')
	list_select_related = ('bundle', 'artwork')


@admin.register(ArtworkOffer)
class ArtworkOfferAdmin(ExportModelAdmin):
	list_display = ('artwork', 'name', 'offer_price', 'email', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('artwork__title', 'name', 'email', 'phone')
	list_select_related = ('artwork',)