# Generated by Django 5.0 on 2024-03-16 00:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0012_alter_activo_eco_unidad'),
        ('requisiciones', '0005_alter_requis_created_by_alter_requis_orden_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='valesalidas',
            name='solicitud',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vale_salida', to='dashboard.order'),
        ),
    ]