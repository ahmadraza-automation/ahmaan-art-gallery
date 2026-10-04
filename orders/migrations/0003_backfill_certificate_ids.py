import uuid

from django.db import migrations, models


def backfill_certificate_ids(apps, schema_editor):
	Order = apps.get_model('orders', 'Order')
	for order_id in Order.objects.filter(certificate_id__isnull=True).values_list('pk', flat=True).iterator():
		Order.objects.filter(pk=order_id, certificate_id__isnull=True).update(certificate_id=uuid.uuid4())


class Migration(migrations.Migration):
	dependencies = [('orders', '0002_order_certificate_file_order_certificate_id_and_more')]

	operations = [
		migrations.RunPython(backfill_certificate_ids, migrations.RunPython.noop),
		migrations.AlterField(
			model_name='order',
			name='certificate_id',
			field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
		),
	]
