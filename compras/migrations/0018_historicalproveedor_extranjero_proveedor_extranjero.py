# Generated by Django 5.0 on 2024-06-04 19:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0017_historicalproveedor_direcciones_arrendamiento_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalproveedor',
            name='extranjero',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='extranjero',
            field=models.BooleanField(default=False),
        ),
    ]
