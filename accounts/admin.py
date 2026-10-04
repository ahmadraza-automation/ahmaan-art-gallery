from django.contrib import admin

from core.admin_utils import ExportModelAdmin
from .models import AccountProfile, SavedAddress


@admin.register(AccountProfile)
class AccountProfileAdmin(ExportModelAdmin):
	list_display = ('user', 'phone', 'city', 'marketing_opt_in', 'created_at')
	list_filter = ('marketing_opt_in', 'city', 'created_at')
	search_fields = ('user__username', 'user__email', 'phone', 'city')
	list_select_related = ('user',)


@admin.register(SavedAddress)
class SavedAddressAdmin(ExportModelAdmin):
	list_display = ('label', 'recipient_name', 'user', 'city', 'phone', 'is_default')
	list_filter = ('city', 'is_default')
	search_fields = ('user__username', 'user__email', 'recipient_name', 'phone', 'address_line1', 'city')
	list_select_related = ('user',)