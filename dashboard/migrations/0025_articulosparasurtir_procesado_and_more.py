# Generated by Django 5.0.1 on 2024-09-05 17:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0024_articulosparasurtir_seleccionado_salida_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='articulosparasurtir',
            name='procesado',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalarticulosparasurtir',
            name='procesado',
            field=models.BooleanField(default=False),
        ),
    ]
