# Generated by Django 5.0 on 2024-01-22 23:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0009_historicalproveedor_direcciones_created_at_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalproveedor_direcciones',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='proveedor_direcciones',
            name='created_at',
        ),
    ]
