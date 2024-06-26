# Generated by Django 5.0.1 on 2024-02-08 23:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gastos', '0016_alter_articulo_gasto_iva'),
    ]

    operations = [
        migrations.AlterField(
            model_name='articulo_gasto',
            name='cantidad',
            field=models.DecimalField(decimal_places=6, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='articulo_gasto',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=6, max_digits=14, null=True),
        ),
    ]
