# Generated by Django 5.0 on 2024-01-05 23:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viaticos', '0023_alter_solicitud_viatico_motivo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitud_viatico',
            name='lugar_comision',
            field=models.TextField(null=True),
        ),
    ]