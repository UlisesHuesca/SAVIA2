# Generated by Django 5.0 on 2024-01-04 19:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viaticos', '0016_alter_viaticos_factura_factura_pdf_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='solicitud_viatico',
            old_name='fecha_inicio_comision',
            new_name='fecha_retorno',
        ),
        migrations.AlterField(
            model_name='solicitud_viatico',
            name='comentario',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='solicitud_viatico',
            name='comentario_hospedaje',
            field=models.TextField(null=True),
        ),
        migrations.CreateModel(
            name='Puntos_Intermedios',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=40)),
                ('solicitud', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='viaticos.solicitud_viatico')),
            ],
        ),
    ]