# Generated by Django 5.0 on 2024-01-07 15:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_tipo_perfil_gerente'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='st_activo',
            field=models.BooleanField(default=False),
        ),
    ]
