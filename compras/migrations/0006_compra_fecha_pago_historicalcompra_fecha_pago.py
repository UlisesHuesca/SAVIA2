# Generated by Django 4.2.8 on 2023-12-07 17:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0005_alter_comparativo_cotizacion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='compra',
            name='fecha_pago',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='historicalcompra',
            name='fecha_pago',
            field=models.DateTimeField(null=True),
        ),
    ]