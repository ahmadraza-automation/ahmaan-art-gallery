from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalog.models import Artist, Artwork, Category
from orders.certificates import generate_order_certificate
from orders.models import Order, OrderItem


class HomeAccessoriesTests(TestCase):
    def setUp(self):
        self.artist = Artist.objects.create(name='Test Artist')
        self.painting_category = Category.objects.create(
            name='Painting Test Category',
            slug='painting-test-category',
            group=Category.Group.PAINTINGS,
        )
        self.accessory_category = Category.objects.create(
            name='Accessory Test Category',
            slug='accessory-test-category',
            group=Category.Group.ACCESSORIES,
        )
        self.painting_artwork = Artwork.objects.create(
            title='Painting Artwork',
            slug='painting-artwork',
            artist=self.artist,
            category=self.painting_category,
            medium='Oil on canvas',
            base_price=Decimal('15000'),
            status=Artwork.Status.AVAILABLE,
            is_one_of_a_kind=True,
        )
        self.accessory_artwork = Artwork.objects.create(
            title='Accessory Artwork',
            slug='accessory-artwork',
            artist=self.artist,
            category=self.accessory_category,
            medium='Brass and glass',
            base_price=Decimal('5000'),
            status=Artwork.Status.AVAILABLE,
            is_one_of_a_kind=True,
        )

    def test_pages_and_filters_return_200(self):
        self.client.get(reverse('gallery:home'))
        response = self.client.get(reverse('gallery:home'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('gallery:shop'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('gallery:shop'), {'group': Category.Group.ACCESSORIES})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('gallery:artwork_detail', args=[self.painting_artwork.slug]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('gallery:artwork_detail', args=[self.accessory_artwork.slug]))
        self.assertEqual(response.status_code, 200)

    def test_navbar_contains_group_names(self):
        response = self.client.get(reverse('gallery:home'))
        html = response.content.decode()
        self.assertIn('Paintings', html)
        self.assertIn('Home Accessories', html)

    def test_accessory_template_hides_artwork_details(self):
        response = self.client.get(reverse('gallery:artwork_detail', args=[self.accessory_artwork.slug]))
        html = response.content.decode()
        self.assertNotIn(self.artist.name, html)
        self.assertNotIn('Certificate of authenticity', html)
        self.assertNotIn('Make an Offer', html)
        self.assertNotIn('Make an offer', html)

        response = self.client.get(reverse('gallery:artwork_detail', args=[self.painting_artwork.slug]))
        html = response.content.decode()
        self.assertIn(self.artist.name, html)
        self.assertIn('Certificate of authenticity', html)
        self.assertIn('Make an Offer', html)

        card_response = self.client.get(reverse('gallery:shop'))
        card_html = card_response.content.decode()
        self.assertNotIn(f'>{self.artist.name}<', card_html)
        self.assertNotIn('Certificate of authenticity', card_html)
        self.assertNotIn('Make an Offer', card_html)

    def test_certificate_generation_handles_accessory_only_orders(self):
        order_without_paintings = Order.objects.create(
            customer_name='Buyer',
            customer_email='buyer@example.com',
            customer_phone='123456789',
            delivery_address='Test address',
            city='Karachi',
            subtotal=Decimal('5000'),
            shipping_amount=Decimal('0'),
            discount_amount=Decimal('0'),
            total=Decimal('5000'),
        )
        OrderItem.objects.create(
            order=order_without_paintings,
            artwork=self.accessory_artwork,
            title_at_order=self.accessory_artwork.title,
            unit_price=self.accessory_artwork.base_price,
            quantity=1,
        )
        self.assertIsNone(generate_order_certificate(order_without_paintings))

        order_with_painting = Order.objects.create(
            customer_name='Buyer',
            customer_email='buyer@example.com',
            customer_phone='123456789',
            delivery_address='Test address',
            city='Karachi',
            subtotal=Decimal('15000'),
            shipping_amount=Decimal('0'),
            discount_amount=Decimal('0'),
            total=Decimal('15000'),
        )
        OrderItem.objects.create(
            order=order_with_painting,
            artwork=self.painting_artwork,
            title_at_order=self.painting_artwork.title,
            unit_price=self.painting_artwork.base_price,
            quantity=1,
        )
        result = generate_order_certificate(order_with_painting)
        self.assertIsNotNone(result)
        self.assertTrue(result.name.endswith('.pdf'))
