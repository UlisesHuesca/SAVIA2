# Generated by Django 5.0.1 on 2024-08-22 19:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0023_activo_fecha_asignacion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='articulosparasurtir',
            name='seleccionado_salida',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalarticulosparasurtir',
            name='seleccionado_salida',
            field=models.BooleanField(default=False),
        ),
    ]
