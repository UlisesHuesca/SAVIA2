# Generated by Django 5.0 on 2024-11-13 19:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0026_historicalproveedor_direcciones_visita_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalproveedor_direcciones',
            name='visita',
        ),
        migrations.RemoveField(
            model_name='proveedor_direcciones',
            name='visita',
        ),
        migrations.AddField(
            model_name='historicalproveedor',
            name='visita',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='visita',
            field=models.BooleanField(default=False),
        ),
    ]
