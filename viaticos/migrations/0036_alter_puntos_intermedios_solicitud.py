# Generated by Django 5.0.1 on 2025-03-19 23:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viaticos', '0035_alter_solicitud_viatico_phone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='puntos_intermedios',
            name='solicitud',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='puntos', to='viaticos.solicitud_viatico'),
        ),
    ]
