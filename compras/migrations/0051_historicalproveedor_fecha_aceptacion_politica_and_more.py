# Generated by Django 5.0.1 on 2025-03-28 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0050_historicalproveedor_acepto_politica_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalproveedor',
            name='fecha_aceptacion_politica',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='fecha_aceptacion_politica',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
