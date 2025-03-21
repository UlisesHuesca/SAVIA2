# Generated by Django 5.0.1 on 2025-02-25 22:19

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0035_historicalproveedor_comprobante_domicilio_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalproveedor',
            name='credencial_acta_constitutiva',
            field=models.TextField(blank=True, max_length=100, null=True, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=('pdf',))]),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='credencial_acta_constitutiva',
            field=models.FileField(blank=True, null=True, upload_to='credencial_acta', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=('pdf',))]),
        ),
    ]
