# Generated by Django 5.0.1 on 2024-06-24 16:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tesoreria', '0009_historicalsaldo_cuenta_comentario_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalsaldo_cuenta',
            name='hecho',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='saldo_cuenta',
            name='hecho',
            field=models.BooleanField(default=False),
        ),
    ]