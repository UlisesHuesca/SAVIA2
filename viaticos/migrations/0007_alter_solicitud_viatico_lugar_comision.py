# Generated by Django 4.2.4 on 2023-10-25 00:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viaticos', '0006_alter_solicitud_viatico_transporte'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitud_viatico',
            name='lugar_comision',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
