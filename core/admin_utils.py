import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html


class ExportModelAdmin(admin.ModelAdmin):
	actions = ('export_as_csv',)

	def get_list_display(self, request):
		columns = list(super().get_list_display(request))
		if any(field.name == 'status' for field in self.model._meta.fields) and 'status_badge' not in columns:
			columns.append('status_badge')
		return columns

	@admin.display(description='Status', ordering='status')
	def status_badge(self, obj):
		value = getattr(obj, 'status', '')
		label = obj.get_status_display() if hasattr(obj, 'get_status_display') else value.replace('_', ' ').title()
		colors = {
			'available': '#16794b', 'approved': '#16794b', 'paid': '#16794b', 'completed': '#16794b',
			'confirmed': '#16794b', 'accepted': '#16794b', 'shipped': '#16794b',
			'pending': '#946200', 'new': '#946200', 'reviewing': '#946200', 'reserved': '#946200',
			'processing': '#245ca6', 'quoted': '#245ca6', 'proof_submitted': '#245ca6',
			'sold': '#666666', 'cancelled': '#a12d2d', 'declined': '#a12d2d', 'rejected': '#a12d2d',
			'unpaid': '#946200', 'refunded': '#666666', 'in_progress': '#245ca6',
		}
		color = colors.get(value, '#555555')
		return format_html('<strong style="color:{}">{}</strong>', color, label)

	@admin.action(description='Export selected rows as CSV')
	def export_as_csv(self, request, queryset):
		response = HttpResponse(content_type='text/csv; charset=utf-8')
		response['Content-Disposition'] = f'attachment; filename="{self.model._meta.model_name}.csv"'
		response.write('\ufeff')
		writer = csv.writer(response)
		fields = list(self.model._meta.concrete_fields)
		writer.writerow([field.verbose_name for field in fields])	
		for obj in queryset.iterator():
			row = []
			for field in fields:
				if field.choices:
					value = getattr(obj, f'get_{field.name}_display')()
				elif field.is_relation and field.many_to_one:
					value = str(getattr(obj, field.name)) if getattr(obj, field.name) else ''
				else:
					value = getattr(obj, field.attname)
				row.append(value)
			writer.writerow(row)
		return response


class SingletonModelAdmin(ExportModelAdmin):
	def has_add_permission(self, request):
		return not self.model.objects.exists()

	def has_delete_permission(self, request, obj=None):
		return False