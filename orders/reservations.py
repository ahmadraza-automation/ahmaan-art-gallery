from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from catalog.models import Artwork
from orders.models import Order

RESERVATION_HOURS = 24


def reserve_unique_artwork(artwork_id, now=None):
	now = now or timezone.now()
	expires_at = now + timedelta(hours=RESERVATION_HOURS)
	with transaction.atomic():
		updated = Artwork.objects.filter(
			pk=artwork_id,
			is_one_of_a_kind=True,
			status=Artwork.Status.AVAILABLE,
		).update(status=Artwork.Status.RESERVED, reserved_until=expires_at)
	return expires_at if updated else None


def release_expired_reservations(now=None):
	now = now or timezone.now()
	with transaction.atomic():
		expired_ids = list(Artwork.objects.filter(
			status=Artwork.Status.RESERVED,
			reserved_until__lte=now,
		).values_list('pk', flat=True))
		if not expired_ids:
			return 0
		updated = Artwork.objects.filter(pk__in=expired_ids, status=Artwork.Status.RESERVED).update(
			status=Artwork.Status.AVAILABLE,
			reserved_until=None,
		)
		Order.objects.filter(
			items__artwork_id__in=expired_ids,
			status__in=(Order.Status.PENDING, Order.Status.CONFIRMED),
			payment_status__in=(Order.PaymentStatus.UNPAID, Order.PaymentStatus.PROOF_SUBMITTED),
		).distinct().update(status=Order.Status.CANCELLED, updated_at=now)
	return updated
