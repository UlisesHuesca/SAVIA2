# Generated by Django 5.0.1 on 2025-02-21 01:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0032_alter_historicalproveedor_rfc_alter_proveedor_rfc'),
        ('user', '0014_pais'),
    ]

    operations = [
        migrations.AddField(
            model_name='estado',
            name='pais',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='user.pais'),
        ),
    ]
