# Generated by Django 4.2.4 on 2023-10-19 18:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Almacen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=25, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Banco',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cuenta_bancaria', models.CharField(blank=True, max_length=25, null=True)),
                ('clabe', models.CharField(blank=True, max_length=22, null=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='profile_images')),
                ('phone', models.CharField(max_length=20, null=True)),
                ('address', models.CharField(blank=True, max_length=200, null=True)),
                ('nivel', models.PositiveSmallIntegerField(default=4)),
                ('puesto', models.CharField(blank=True, max_length=40, null=True)),
                ('banco', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='user.banco')),
            ],
        ),
        migrations.CreateModel(
            name='Distrito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=20, null=True)),
                ('abreviado', models.CharField(max_length=3, null=True)),
                ('responsable', models.CharField(max_length=20, null=True)),
                ('status', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Empresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(blank=True, max_length=30, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Tipo_perfil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, null=True)),
                ('inicio_estadisticas', models.BooleanField(default=False, null=True)),
                ('calidad', models.BooleanField(default=False, null=True)),
                ('configuracion', models.BooleanField(default=False, null=True)),
                ('almacen', models.BooleanField(default=False, null=True)),
                ('solicitudes', models.BooleanField(default=False, null=True)),
                ('requisiciones', models.BooleanField(default=False, null=True)),
                ('compras', models.BooleanField(default=False, null=True)),
                ('tesoreria', models.BooleanField(default=False, null=True)),
                ('autorizacion', models.BooleanField(default=False, null=True)),
                ('reportes', models.BooleanField(default=False, null=True)),
                ('historicos', models.BooleanField(default=False, null=True)),
                ('proveedores', models.BooleanField(default=False, null=True)),
                ('supervisor', models.BooleanField(default=False, null=True)),
                ('superintendente', models.BooleanField(default=False, null=True)),
                ('almacenista', models.BooleanField(default=False, null=True)),
                ('comprador', models.BooleanField(default=False, null=True)),
                ('oc_superintendencia', models.BooleanField(default=False, null=True)),
                ('oc_gerencia', models.BooleanField(default=False, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('almacen', models.ManyToManyField(related_name='almacenes', to='user.almacen')),
                ('distritos', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.distrito')),
                ('staff', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.customuser')),
                ('tipo', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.tipo_perfil')),
            ],
        ),
        migrations.AddField(
            model_name='customuser',
            name='empresa',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.empresa'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='staff',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='almacen',
            name='distrito',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.distrito'),
        ),
    ]
