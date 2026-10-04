from django.db import migrations


def add_default_curator_content(apps, schema_editor):
    ArtMatchQuestion = apps.get_model('core', 'ArtMatchQuestion')
    ArtMatchOption = apps.get_model('core', 'ArtMatchOption')
    CuratorAdviceBanner = apps.get_model('core', 'CuratorAdviceBanner')

    default_questions = (
        {
            'key': 'room',
            'prompt': 'What room are you styling?',
            'order': 1,
            'options': (
                ('living-room', 'Living room'),
                ('bedroom', 'Bedroom'),
                ('dining-room', 'Dining room'),
                ('workspace', 'Workspace'),
            ),
        },
        {
            'key': 'style',
            'prompt': 'Which style feels closest to home?',
            'order': 2,
            'options': (
                ('minimal', 'Minimal and quiet'),
                ('warm-modern', 'Warm modern'),
                ('statement', 'Bold and statement-led'),
                ('earthy', 'Earthy and layered'),
            ),
        },
        {
            'key': 'color',
            'prompt': 'Which palette are you leaning toward?',
            'order': 3,
            'options': (
                ('soft neutrals', 'Soft neutrals'),
                ('deep jewel', 'Deep jewel tones'),
                ('earthy natural', 'Earthy natural tones'),
                ('contrast pops', 'Contrast pops'),
            ),
        },
        {
            'key': 'budget',
            'prompt': 'What is your ideal budget range?',
            'order': 4,
            'options': (
                ('25000-50000', 'PKR 25,000 - 50,000'),
                ('50000-100000', 'PKR 50,000 - 100,000'),
                ('100000-200000', 'PKR 100,000 - 200,000'),
                ('200000-plus', 'PKR 200,000 and above'),
            ),
        },
        {
            'key': 'size',
            'prompt': 'How much wall space do you want to fill?',
            'order': 5,
            'options': (
                ('small', 'Small accent piece'),
                ('medium', 'Medium statement work'),
                ('large', 'Large focal piece'),
                ('oversized', 'Oversized anchor piece'),
            ),
        },
    )

    for question_data in default_questions:
        question, _ = ArtMatchQuestion.objects.get_or_create(
            key=question_data['key'],
            defaults={'prompt': question_data['prompt'], 'order': question_data['order'], 'is_active': True},
        )
        question.prompt = question_data['prompt']
        question.order = question_data['order']
        question.is_active = True
        question.save(update_fields=['prompt', 'order', 'is_active'])
        for option_order, (value, label) in enumerate(question_data['options']):
            ArtMatchOption.objects.get_or_create(
                question=question,
                value=value,
                defaults={'label': label, 'order': option_order},
            )

    CuratorAdviceBanner.objects.update_or_create(
        is_active=True,
        defaults={
            'heading': 'Need a second opinion?',
            'text': 'Tell us about your room, the work you love, and what you are looking for.',
            'whatsapp_message': 'Hello, I would like some free art advice.',
            'button_text': 'Talk to a Curator',
        },
    )


def reverse_default_curator_content(apps, schema_editor):
    ArtMatchOption = apps.get_model('core', 'ArtMatchOption')
    ArtMatchQuestion = apps.get_model('core', 'ArtMatchQuestion')
    CuratorAdviceBanner = apps.get_model('core', 'CuratorAdviceBanner')

    CuratorAdviceBanner.objects.all().delete()
    ArtMatchOption.objects.all().delete()
    ArtMatchQuestion.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_artmatchquestion_consultationrequest_and_more'),
    ]

    operations = [
        migrations.RunPython(add_default_curator_content, reverse_default_curator_content),
    ]
