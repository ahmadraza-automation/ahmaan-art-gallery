from django.core.management.base import BaseCommand

from catalog.models import (
	Artist, Artwork, ArtworkBundle, ArtworkBundleItem, CanvasType, Category,
	Collection, FrameOption, SizeOption,
)
from core.models import JournalPost, WelcomeOffer


class Command(BaseCommand):
	help = 'Create four collections, three artists, and twelve example artworks.'

	def handle(self, *args, **options):
		categories = {
			name: Category.objects.update_or_create(slug=slug, defaults={'name': name, 'is_active': True})[0]
			for name, slug in (
				('Oil Paintings', 'oil-paintings'),
				('Calligraphy', 'calligraphy'),
				('Digital Art', 'digital-art'),
				('Handmade Sketches', 'handmade-sketches'),
				('Custom Portraits', 'custom-portraits'),
			)
		}
		artists = [
			Artist.objects.update_or_create(slug='sana-raza', defaults={'name': 'Sana Raza', 'specialty': 'Oil and natural forms'})[0],
			Artist.objects.update_or_create(slug='hamza-qadri', defaults={'name': 'Hamza Qadri', 'specialty': 'Contemporary calligraphy'})[0],
			Artist.objects.update_or_create(slug='maira-khan', defaults={'name': 'Maira Khan', 'specialty': 'Drawing and digital composition'})[0],
		]
		collections = [
			Collection.objects.update_or_create(slug=slug, defaults={'name': name, 'short_description': description, 'is_featured': index == 0, 'order': index})[0]
			for index, (name, slug, description) in enumerate((
				('Quiet Landscapes', 'quiet-landscapes', 'Atmospheric views shaped by soft light and open space.'),
				('Letters of Light', 'letters-of-light', 'Calligraphic works grounded in rhythm, line, and reflection.'),
				('Everyday Reverie', 'everyday-reverie', 'Small moments remade through color and imagination.'),
				('Portrait Studies', 'portrait-studies', 'Expressive studies of character, memory, and presence.'),
			))
		]
		artworks = [
			('Blue Hour Courtyard', 'A hush settles over the courtyard as evening gathers.', 'Oil Paintings', 0, 'Oil on canvas', 28500, 'Blue hour brings the garden into quiet focus.'),
			('Rain on the Old Road', 'A familiar lane glimmers after a brief summer rain.', 'Oil Paintings', 0, 'Oil on canvas', 32000, 'A gentle pause between rain and return.'),
			('Window Facing North', 'Cool daylight traces the edges of a lived-in room.', 'Oil Paintings', 0, 'Oil on canvas', 24000, 'Stillness, held in a square of northern light.'),
			('The Fig Tree', 'A patient tree opens its branches to the last warmth of day.', 'Oil Paintings', 0, 'Oil and cold wax', 36000, 'Rooted, generous, and unhurried.'),
			('Noor in Bloom', 'A flowing composition carries a sense of renewal.', 'Calligraphy', 1, 'Ink and gouache on paper', 18000, 'A luminous word finding its way into spring.'),
			('Lines of Patience', 'Measured strokes give the page a calm, steady pulse.', 'Calligraphy', 1, 'Ink on handmade paper', 22000, 'A quiet rhythm for a considered room.'),
			('Between Two Prayers', 'Balanced forms leave space for reflection.', 'Calligraphy', 1, 'Gouache and gold leaf', 29500, 'A pause shaped by devotion and light.'),
			('Garden of Names', 'Letters gather like leaves across a deep green field.', 'Calligraphy', 1, 'Acrylic and ink on canvas', 34000, 'Many stories, meeting in one garden.'),
			('Small Sun, Late Morning', 'A bright study catches the ease of a slow morning.', 'Digital Art', 2, 'Archival pigment print', 12500, 'Warm light, with nowhere urgent to be.'),
			('A Place to Begin', 'Layered color suggests a new path through familiar ground.', 'Digital Art', 2, 'Archival pigment print', 15000, 'The first page of a hopeful day.'),
			('Hands at Rest', 'A graphite portrait honors an unguarded moment.', 'Handmade Sketches', 2, 'Graphite on cotton paper', 19500, 'Tenderness in the space between gestures.'),
			('The Blue Shawl', 'A close portrait keeps the warmth of a remembered visit.', 'Handmade Sketches', 2, 'Charcoal and pastel', 21000, 'A face remembered with affection.'),
		]
		for index, (title, tagline, category_name, artist_index, medium, price, story) in enumerate(artworks):
			artwork, _ = Artwork.objects.update_or_create(
				slug=title.lower().replace(' ', '-').replace(',', ''),
				defaults={
					'title': title,
					'mood_tagline': tagline,
					'story': story,
					'artist': artists[artist_index],
					'category': categories[category_name],
					'medium': medium,
					'year': 2026,
					'width': 40 + (index % 3) * 10,
					'height': 50 + (index % 4) * 5,
					'base_price': price,
					'color_palette_tags': ['indigo', 'warm white'] if index % 2 == 0 else ['sage', 'umber'],
					'mood_tags': ['calm', 'reflective'] if index % 2 == 0 else ['warm', 'hopeful'],
					'space_tags': ['home', 'gallery'],
					'is_one_of_a_kind': True,
					'quantity': 1,
					'is_featured': index in (0, 4, 8),
					'is_best_seller': index in (1, 4, 8),
				})
			artwork.collections.set([collections[3] if index == 11 else collections[artist_index]])
		for name, width, height, modifier in (
			('Small', 30, 40, 0), ('Medium', 40, 50, 3500), ('Large', 50, 70, 7000),
		):
			SizeOption.objects.update_or_create(name=name, defaults={'width': width, 'height': height, 'price_modifier': modifier, 'is_active': True})
		for name, modifier in (('No frame', 0), ('Black frame', 2500), ('Natural wood', 4500)):
			FrameOption.objects.update_or_create(name=name, defaults={'price_modifier': modifier, 'is_active': True})
		for name, description, modifier in (
			('Cotton canvas', 'Gallery-wrapped cotton canvas.', 0),
			('Fine art paper', 'Archival matte paper for works on paper.', 1500),
			('Canvas board', 'Rigid, lightweight canvas board.', 500),
		):
			CanvasType.objects.update_or_create(name=name, defaults={'description': description, 'price_modifier': modifier, 'is_active': True})
		bundle, _ = ArtworkBundle.objects.update_or_create(
			slug='morning-light-pair',
			defaults={'name': 'The Morning Light Pair', 'short_description': 'Two bright studies for a room that welcomes the day.', 'bundle_price': 25000, 'is_featured': True, 'is_active': True},
		)
		bundle.bundle_items.all().delete()
		for position, slug in enumerate(('small-sun-late-morning', 'a-place-to-begin')):
			ArtworkBundleItem.objects.create(bundle=bundle, artwork=Artwork.objects.get(slug=slug), order=position)
		bundle.full_clean()
		journal_posts = (
			('A slower way to find art', 'Good art asks for a little time. Here are a few gentle ways to notice what keeps drawing you back.', 'Choosing a work for your home is less about matching and more about paying attention. Notice the colors you return to, the scenes that make you pause, and the pieces that feel different each time you see them.'),
			('Inside the artist studio', 'A look at the small rituals, unfinished studies, and patient decisions behind a finished piece.', 'Every studio has its own rhythm. Some days begin with a line in a sketchbook; others with a canvas turned toward the light. We ask our artists to share the process and the discoveries that stay with them.'),
			('Living with one-of-a-kind work', 'Original art changes with the light, the season, and the life happening around it.', 'A one-of-a-kind work does not need a special occasion. Give it a wall where the daylight shifts, leave it room to breathe, and let it become part of the ordinary moments that make a home.'),
		)
		for title, excerpt, body in journal_posts:
			JournalPost.objects.update_or_create(slug=title.lower().replace(' ', '-'), defaults={'title': title, 'excerpt': excerpt, 'body': body, 'is_published': True})
		if not WelcomeOffer.objects.exists():
			WelcomeOffer.objects.create(
				title='A first look, with us',
				message='Join our occasional gallery letters for new work, studio stories, and early looks at each collection.',
				button_text='Join the newsletter',
			)
		self.stdout.write(self.style.SUCCESS('Seeded 4 collections, 3 artists, 5 categories, 12 artworks, customization options, one curated set, 3 journal posts, and the welcome offer.'))