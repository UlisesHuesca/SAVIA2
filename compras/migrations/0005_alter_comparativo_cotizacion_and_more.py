# Generated by Django 4.2.4 on 2023-11-22 14:21

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0004_comparativo_cotizacion4_comparativo_cotizacion5'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comparativo',
            name='cotizacion',
            field=models.FileField(blank=True, null=True, upload_to='comparativos', validators=[django.core.validators.FileExtensionValidator(['pdf'])]),
        ),
        migrations.AlterField(
            model_name='comparativo',
            name='cotizacion2',
            field=models.FileField(blank=True, null=True, upload_to='comparativos', validators=[django.core.validators.FileExtensionValidator(['pdf'])]),
        ),
        migrations.AlterField(
            model_name='comparativo',
            name='cotizacion3',
            field=models.FileField(null=True, upload_to='comparativos', validators=[django.core.validators.FileExtensionValidator(['pdf'])]),
        ),
        migrations.AlterField(
            model_name='comparativo',
            name='cotizacion4',
            field=models.FileField(null=True, upload_to='comparativos'),
        ),
        migrations.AlterField(
            model_name='comparativo',
            name='cotizacion5',
            field=models.FileField(null=True, upload_to='comparativos'),
        ),
    ]
