from django.core.management.base import BaseCommand

from orders.reservations import release_expired_reservations


class Command(BaseCommand):
	help = 'Release catalog artworks whose 24-hour unpaid reservation has expired.'

	def handle(self, *args, **options):
		released = release_expired_reservations()
		self.stdout.write(self.style.SUCCESS(f'Released {released} expired reservation(s).'))
