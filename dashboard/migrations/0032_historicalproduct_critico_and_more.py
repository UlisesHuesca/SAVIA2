# Generated by Django 5.0 on 2024-11-05 21:02

import dashboard.models
import django.core.validators
import django.db.models.deletion
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0031_alter_historicalorder_last_folio_number_and_more'),
        ('user', '0010_rename_sustituto_de_profile_sustituto'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalproduct',
            name='critico',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalproduct',
            name='rev_calidad',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='product',
            name='critico',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='product',
            name='rev_calidad',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='HistoricalProducto_Calidad',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('created_at', models.DateTimeField(blank=True, editable=False)),
                ('updated_at', models.DateTimeField(null=True)),
                ('requisitos', models.TextField(blank=True, null=True)),
                ('history_change_reason', models.TextField(null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('producto', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='dashboard.product')),
                ('updated_by', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='user.profile')),
            ],
            options={
                'verbose_name': 'historical producto_ calidad',
                'verbose_name_plural': 'historical producto_ calidads',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='Producto_Calidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(null=True)),
                ('requisitos', models.TextField(blank=True, null=True)),
                ('producto', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='producto_calidad', to='dashboard.product')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.profile')),
            ],
        ),
        migrations.CreateModel(
            name='Requerimiento_Calidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, null=True, unique=True)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('url', models.FileField(unique=True, upload_to='bonos/', validators=[dashboard.models.validar_size, django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg', 'jpeg', 'xls', 'xlsx'])])),
                ('updated_at', models.DateTimeField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('solicitud', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requerimientos_calidad', to='dashboard.producto_calidad')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.profile')),
            ],
        ),
    ]
