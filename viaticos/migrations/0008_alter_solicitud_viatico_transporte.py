# Generated by Django 4.2.4 on 2023-10-25 01:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viaticos', '0007_alter_solicitud_viatico_lugar_comision'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitud_viatico',
            name='transporte',
            field=models.CharField(max_length=90, null=True),
        ),
    ]