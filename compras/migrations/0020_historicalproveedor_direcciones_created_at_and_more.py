# Generated by Django 5.0 on 2024-07-23 18:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0019_historicalproveedor_direcciones_moneda_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalproveedor_direcciones',
            name='created_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='proveedor_direcciones',
            name='created_at',
            field=models.DateTimeField(null=True),
        ),
    ]