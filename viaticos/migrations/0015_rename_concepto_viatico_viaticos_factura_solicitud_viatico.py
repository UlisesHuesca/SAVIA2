# Generated by Django 4.2.4 on 2023-10-27 01:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('viaticos', '0014_alter_viaticos_factura_concepto_viatico'),
    ]

    operations = [
        migrations.RenameField(
            model_name='viaticos_factura',
            old_name='concepto_viatico',
            new_name='solicitud_viatico',
        ),
    ]
