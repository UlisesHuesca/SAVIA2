# Generated by Django 5.0.1 on 2024-03-03 02:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitudes', '0002_alter_subproyecto_descripcion_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subproyecto',
            name='descripcion',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]