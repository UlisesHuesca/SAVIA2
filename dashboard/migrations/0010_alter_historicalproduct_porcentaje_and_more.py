# Generated by Django 5.0.1 on 2024-02-04 03:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0009_alter_historicalorder_created_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalproduct',
            name='porcentaje',
            field=models.DecimalField(decimal_places=2, max_digits=4, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='porcentaje',
            field=models.DecimalField(decimal_places=2, max_digits=4, null=True),
        ),
    ]
