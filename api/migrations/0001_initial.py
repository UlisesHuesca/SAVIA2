# Generated by Django 5.0 on 2024-10-22 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TablaFestivos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dia_festivo', models.DateField(db_index=True, null=True)),
            ],
        ),
    ]
