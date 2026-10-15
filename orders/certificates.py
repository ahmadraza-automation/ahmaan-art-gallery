from io import BytesIO

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def generate_order_certificate(order):
	if order.certificate_file:
		return order.certificate_file

	buffer = BytesIO()
	page = canvas.Canvas(buffer, pagesize=A4)
	page.setTitle(f'Certificate of Authenticity {order.certificate_id}')
	page.setFillColorRGB(.17, .24, .21)
	page.setFont('Helvetica-Bold', 22)
	page.drawString(54, 780, 'AHMAAN ART GALLERY')
	page.setFont('Times-Roman', 25)
	page.drawString(54, 725, 'Certificate of Authenticity')
	page.setFont('Helvetica', 11)
	page.setFillColorRGB(.28, .31, .28)
	page.drawString(54, 694, f'Certificate ID: {order.certificate_id}')
	page.drawString(54, 675, f'Order: {order.reference}')
	page.drawString(54, 656, f'Issued: {order.created_at:%d %B %Y}')
	page.setStrokeColorRGB(.69, .55, .34)
	page.line(54, 637, 540, 637)
	page.setFillColorRGB(.17, .24, .21)
	page.setFont('Helvetica-Bold', 12)
	page.drawString(54, 610, 'Original works in this order')
	page.setFont('Helvetica', 11)
	y = 583
	painting_items = []
	for item in order.items.select_related('artwork', 'artwork__artist', 'artwork__category'):
		if item.artwork and item.artwork.category_id and item.artwork.category.group == 'accessories':
			continue
		painting_items.append(item)
	for item in painting_items:
		artist_name = item.artwork.artist.name if item.artwork else 'Ahmaan Art Gallery'
		page.drawString(64, y, f'{item.title_at_order}  |  {artist_name}')
		y -= 20
		if y < 150:
			page.showPage()
			y = 770
	if not painting_items:
		return None
	page.setFont('Helvetica', 9)
	page.setFillColorRGB(.35, .38, .35)
	page.drawString(54, 105, 'This certificate verifies the original artwork listed above as supplied by Ahmaan Art Gallery.')
	verify_path = reverse('orders:verify_certificate', args=[order.certificate_id])
	verify_url = f'{settings.PUBLIC_SITE_URL.rstrip("/")}{verify_path}'
	qr = qrcode.make(verify_url)
	qr_buffer = BytesIO()
	qr.save(qr_buffer, format='PNG')
	qr_buffer.seek(0)
	page.drawImage(ImageReader(qr_buffer), 454, 92, width=78, height=78, mask='auto')
	page.setFont('Helvetica', 8)
	page.drawString(54, 88, f'Verify: {verify_url}')
	page.save()
	buffer.seek(0)
	order.certificate_file.save(f'{order.certificate_id}.pdf', ContentFile(buffer.read()), save=True)
	return order.certificate_file
