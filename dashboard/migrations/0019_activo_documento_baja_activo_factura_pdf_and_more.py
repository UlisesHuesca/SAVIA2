# Generated by Django 5.0 on 2024-04-04 21:07

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0018_alter_activo_marca'),
    ]

    operations = [
        migrations.AddField(
            model_name='activo',
            name='documento_baja',
            field=models.FileField(blank=True, null=True, upload_to='bajas_activos', validators=[django.core.validators.FileExtensionValidator(['pdf'])]),
        ),
        migrations.AddField(
            model_name='activo',
            name='factura_pdf',
            field=models.FileField(blank=True, null=True, upload_to='pdf_activos', validators=[django.core.validators.FileExtensionValidator(['pdf'])]),
        ),
        migrations.AddField(
            model_name='activo',
            name='factura_xml',
            field=models.FileField(blank=True, null=True, upload_to='xml_activos', validators=[django.core.validators.FileExtensionValidator(['xml'])]),
        ),
        migrations.AddField(
            model_name='historicalactivo',
            name='documento_baja',
            field=models.TextField(blank=True, max_length=100, null=True, validators=[django.core.validators.FileExtensionValidator(['pdf'])]),
        ),
        migrations.AddField(
            model_name='historicalactivo',
            name='factura_pdf',
            field=models.TextField(blank=True, max_length=100, null=True, validators=[django.core.validators.FileExtensionValidator(['pdf'])]),
        ),
        migrations.AddField(
            model_name='historicalactivo',
            name='factura_xml',
            field=models.TextField(blank=True, max_length=100, null=True, validators=[django.core.validators.FileExtensionValidator(['xml'])]),
        ),
    ]