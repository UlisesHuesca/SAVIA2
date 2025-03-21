# Generated by Django 5.0.1 on 2025-02-25 23:44

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0036_historicalproveedor_credencial_acta_constitutiva_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Evidencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='evidencias', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=('pdf',))])),
                ('uploaded', models.DateField(auto_now_add=True)),
                ('activated', models.BooleanField(default=False)),
                ('oc', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='evidencias', to='compras.compra')),
            ],
        ),
    ]
