# Generated by Django 5.0 on 2024-11-06 16:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0032_historicalproduct_critico_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='requerimiento_calidad',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='requerimiento_calidad',
            name='updated_at',
        ),
    ]
