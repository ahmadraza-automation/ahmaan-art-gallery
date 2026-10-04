from django.contrib import admin

from core.admin_utils import ExportModelAdmin
from .models import Coupon, GiftCard, GiftCardRedemption, Order, OrderItem, PaymentProof


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0


class PaymentProofInline(admin.TabularInline):
	model = PaymentProof
	extra = 0
	readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(ExportModelAdmin):
	list_display = ('reference', 'customer_name', 'total', 'status', 'payment_status', 'created_at')
	list_filter = ('status', 'payment_status', 'created_at')
	search_fields = ('reference', 'customer_name', 'customer_email', 'customer_phone')
	readonly_fields = ('reference', 'created_at', 'updated_at')
	inlines = (OrderItemInline, PaymentProofInline)
	change_list_template = 'admin/orders/order/change_list.html'
	actions = ('export_as_csv', 'mark_confirmed', 'mark_in_progress', 'mark_shipped', 'mark_delivered')

	@admin.action(description='Mark selected orders confirmed')
	def mark_confirmed(self, request, queryset):
		queryset.update(status=Order.Status.CONFIRMED)

	@admin.action(description='Mark selected orders in progress')
	def mark_in_progress(self, request, queryset):
		queryset.update(status=Order.Status.IN_PROGRESS)

	@admin.action(description='Mark selected orders shipped')
	def mark_shipped(self, request, queryset):
		queryset.update(status=Order.Status.SHIPPED)

	@admin.action(description='Mark selected orders delivered')
	def mark_delivered(self, request, queryset):
		queryset.update(status=Order.Status.DELIVERED)

	def changelist_view(self, request, extra_context=None):
		from orders.views import analytics_data
		return super().changelist_view(request, extra_context={**(extra_context or {}), 'sales_analytics': analytics_data()})


@admin.register(OrderItem)
class OrderItemAdmin(ExportModelAdmin):
	list_display = ('title_at_order', 'order', 'artwork', 'quantity', 'unit_price', 'chosen_size', 'chosen_frame')
	list_filter = ('chosen_size', 'chosen_frame')
	search_fields = ('title_at_order', 'order__reference', 'artwork__title')
	list_select_related = ('order', 'artwork', 'chosen_size', 'chosen_frame')


@admin.register(Coupon)
class CouponAdmin(ExportModelAdmin):
	list_display = ('code', 'issued_to_email', 'discount_percent', 'discount_amount', 'uses', 'usage_limit', 'is_active', 'expires_at')
	list_filter = ('is_active', 'starts_at', 'expires_at')
	search_fields = ('code', 'issued_to_email')


@admin.register(GiftCard)
class GiftCardAdmin(ExportModelAdmin):
	list_display = ('code', 'amount', 'is_active', 'is_redeemed', 'recipient_email', 'created_at')
	list_filter = ('is_active', 'is_redeemed', 'created_at')
	search_fields = ('code', 'recipient_name', 'recipient_email', 'message')
	readonly_fields = ('code', 'created_at', 'redeemed_at')


@admin.register(GiftCardRedemption)
class GiftCardRedemptionAdmin(ExportModelAdmin):
	list_display = ('gift_card', 'order', 'amount_applied', 'redeemed_at')
	list_filter = ('redeemed_at',)
	search_fields = ('gift_card__code', 'order__reference')


@admin.register(PaymentProof)
class PaymentProofAdmin(ExportModelAdmin):
	list_display = ('order', 'amount', 'status', 'created_at')
	list_filter = ('status', 'created_at')
	search_fields = ('order__reference', 'reference_note')
	list_select_related = ('order',)
	actions = ('export_as_csv', 'approve_proofs', 'reject_proofs')

	@admin.action(description='Approve selected payment proofs')
	def approve_proofs(self, request, queryset):
		order_ids = list(queryset.values_list('order_id', flat=True).distinct())
		queryset.update(status=PaymentProof.Status.APPROVED)
		Order.objects.filter(pk__in=order_ids).update(payment_status=Order.PaymentStatus.PAID, status=Order.Status.CONFIRMED)

	@admin.action(description='Reject selected payment proofs')
	def reject_proofs(self, request, queryset):
		queryset.update(status=PaymentProof.Status.REJECTED)