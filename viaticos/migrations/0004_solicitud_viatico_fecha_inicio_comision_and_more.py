# Generated by Django 4.2.4 on 2023-10-25 00:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viaticos', '0003_solicitud_viatico_comentario_hospedaje_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitud_viatico',
            name='fecha_inicio_comision',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='solicitud_viatico',
            name='motivo',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='solicitud_viatico',
            name='fecha_partida',
            field=models.DateField(null=True),
        ),
    ]