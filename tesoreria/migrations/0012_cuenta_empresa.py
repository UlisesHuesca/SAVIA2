# Generated by Django 5.0 on 2024-06-27 16:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tesoreria', '0011_historicalsaldo_cuenta_fecha_inicial_and_more'),
        ('user', '0010_rename_sustituto_de_profile_sustituto'),
    ]

    operations = [
        migrations.AddField(
            model_name='cuenta',
            name='empresa',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.empresa'),
        ),
    ]