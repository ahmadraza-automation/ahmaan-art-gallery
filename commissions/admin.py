from django.contrib import admin

from core.admin_utils import ExportModelAdmin
from .models import CommissionReferenceImage, CommissionRequest


class CommissionReferenceInline(admin.TabularInline):
	model = CommissionReferenceImage
	extra = 0


@admin.register(CommissionRequest)
class CommissionRequestAdmin(ExportModelAdmin):
	list_display = ('id', 'customer_name', 'art_type', 'budget', 'quote_amount', 'deadline', 'status', 'created_at')
	list_filter = ('status', 'art_type', 'created_at')
	search_fields = ('customer_name', 'customer_email', 'customer_phone', 'description')
	inlines = (CommissionReferenceInline,)


@admin.register(CommissionReferenceImage)
class CommissionReferenceImageAdmin(ExportModelAdmin):
	list_display = ('request', 'caption')
	search_fields = ('request__customer_name', 'caption')
	list_select_related = ('request',)