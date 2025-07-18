# Generated by Django 5.0 on 2025-07-16 20:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0061_compra_comentario_cierre_and_more'),
        ('finanzas', '0003_alter_exhibit_tipo'),
        ('user', '0024_tipo_perfil_finanzas'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='exhibit',
            name='concepto_flujo',
        ),
        migrations.RemoveField(
            model_name='exhibit',
            name='descripcion',
        ),
        migrations.RemoveField(
            model_name='exhibit',
            name='id_detalle',
        ),
        migrations.RemoveField(
            model_name='exhibit',
            name='monto',
        ),
        migrations.RemoveField(
            model_name='exhibit',
            name='nombre_proveedor',
        ),
        migrations.RemoveField(
            model_name='exhibit',
            name='observaciones',
        ),
        migrations.RemoveField(
            model_name='exhibit',
            name='proveedor',
        ),
        migrations.RemoveField(
            model_name='exhibit',
            name='solicitud',
        ),
        migrations.RemoveField(
            model_name='exhibit',
            name='tipo',
        ),
        migrations.AddField(
            model_name='exhibit',
            name='creada_por',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Exhibits', to='user.profile'),
        ),
        migrations.AddField(
            model_name='exhibit',
            name='created_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='exhibit',
            name='folio',
            field=models.IntegerField(null=True),
        ),
        migrations.CreateModel(
            name='Linea_Exhibit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('Vordcab', 'Vordcab'), ('PROVEEDOR', 'Proveedor'), ('VACIO', 'Vacío')], max_length=10)),
                ('solicitud', models.CharField(max_length=20)),
                ('id_detalle', models.PositiveIntegerField()),
                ('monto', models.DecimalField(decimal_places=2, max_digits=12)),
                ('concepto_flujo', models.CharField(max_length=50)),
                ('descripcion', models.TextField()),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('nombre_proveedor', models.CharField(max_length=255)),
                ('proveedor', models.ForeignKey(blank=True, help_text='Solo se llena si el tipo es PROVEEDOR', null=True, on_delete=django.db.models.deletion.SET_NULL, to='compras.proveedor_direcciones')),
            ],
        ),
    ]
