from io import BytesIO
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


IMAGE_WIDTHS = (2400, 1200, 600, 320)


def optimize_uploaded_image(instance, field_name):
	field_file = getattr(instance, field_name)
	if not field_file or not field_file.name or field_file._committed:
		return

	image = ImageOps.exif_transpose(Image.open(field_file))
	if image.mode not in ('RGB', 'RGBA'):
		image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')

	field = instance._meta.get_field(field_name)
	original_stem = PurePosixPath(field_file.name).stem
	webp_name = f'{original_stem}.webp'
	primary_name = field.generate_filename(instance, webp_name)
	storage = field.storage

	for width in IMAGE_WIDTHS:
		variant = image.copy()
		if variant.width > width:
			height = round(variant.height * width / variant.width)
			variant = variant.resize((width, height), Image.Resampling.LANCZOS)
		buffer = BytesIO()
		variant.save(buffer, format='WEBP', quality=84, method=6)
		if width == IMAGE_WIDTHS[0]:
			instance.__dict__[field_name] = ContentFile(buffer.getvalue(), name=webp_name)
		else:
			variant_path = PurePosixPath(primary_name)
			variant_name = str(variant_path.with_name(f'{variant_path.stem}-{width}.webp'))
			storage.save(variant_name, ContentFile(buffer.getvalue()))


def responsive_srcset(field_file):
	if not field_file or not field_file.name or not field_file.name.lower().endswith('.webp'):
		return ''
	path = PurePosixPath(field_file.name)
	storage = field_file.storage
	original_width = field_file.width
	variants = []
	for width in (320, 600, 1200):
		if width < original_width:
			name = str(path.with_name(f'{path.stem}-{width}.webp'))
			variants.append(f'{storage.url(name)} {width}w')
	variants.append(f'{field_file.url} {original_width}w')
	return ', '.join(variants)