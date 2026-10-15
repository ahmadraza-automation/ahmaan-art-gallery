from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0010_artist_city_artist_interview_article'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='group',
            field=models.CharField(
                choices=[('paintings', 'Paintings'), ('accessories', 'Home Accessories')],
                default='paintings',
                max_length=20,
                db_index=True,
            ),
        ),
    ]
