# Generated by Django 5.0 on 2024-06-05 01:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0018_historicalproveedor_extranjero_proveedor_extranjero'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalproveedor_direcciones',
            name='moneda',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='compras.moneda'),
        ),
        migrations.AddField(
            model_name='proveedor_direcciones',
            name='moneda',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='compras.moneda'),
        ),
    ]
