# Generated by Django 5.0 on 2024-01-17 23:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0012_alter_articulo_gasto_producto_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitud_gasto',
            name='folio',
            field=models.IntegerField(null=True),
        ),
    ]