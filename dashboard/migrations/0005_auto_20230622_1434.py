# Generated by Django 3.2.5 on 2023-06-22 20:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_auto_20230516_1804'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalorder',
            name='last_folio_number',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='last_folio_number',
            field=models.IntegerField(null=True),
        ),
    ]