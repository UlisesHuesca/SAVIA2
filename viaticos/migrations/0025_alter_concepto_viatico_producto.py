# Generated by Django 5.0 on 2024-02-14 01:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0010_alter_historicalproduct_porcentaje_and_more'),
        ('viaticos', '0024_alter_solicitud_viatico_lugar_comision'),
    ]

    operations = [
        migrations.AlterField(
            model_name='concepto_viatico',
            name='producto',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.product'),
        ),
    ]
