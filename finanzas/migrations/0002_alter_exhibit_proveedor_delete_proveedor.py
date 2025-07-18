# Generated by Django 5.0 on 2025-06-25 00:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0061_compra_comentario_cierre_and_more'),
        ('finanzas', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exhibit',
            name='proveedor',
            field=models.ForeignKey(blank=True, help_text='Solo se llena si el tipo es PROVEEDOR', null=True, on_delete=django.db.models.deletion.SET_NULL, to='compras.proveedor_direcciones'),
        ),
        migrations.DeleteModel(
            name='Proveedor',
        ),
    ]
