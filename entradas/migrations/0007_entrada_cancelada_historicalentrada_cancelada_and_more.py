# Generated by Django 5.0.1 on 2024-05-10 21:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entradas', '0006_cierre_nc_historicalno_conformidad_image_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='entrada',
            name='cancelada',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalentrada',
            name='cancelada',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalno_conformidad',
            name='fecha_cierre',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='no_conformidad',
            name='fecha_cierre',
            field=models.DateField(blank=True, null=True),
        ),
    ]