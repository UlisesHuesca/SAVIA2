# Generated by Django 5.0.1 on 2025-04-15 23:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0051_historicalproveedor_fecha_aceptacion_politica_and_more'),
        ('user', '0021_tipo_perfil_proveedores_edicion'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalproveedor',
            name='perfil_proveedor',
        ),
        migrations.RemoveField(
            model_name='proveedor',
            name='perfil_proveedor',
        ),
        migrations.AlterField(
            model_name='proveedor',
            name='creado_por',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='creado_por', to='user.profile'),
        ),
    ]
