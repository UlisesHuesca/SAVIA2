# Generated by Django 5.0.1 on 2025-03-10 23:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0045_documentosproveedor_comentario'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalproveedor',
            name='comentario_csf',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='proveedor',
            name='comentario_csf',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
