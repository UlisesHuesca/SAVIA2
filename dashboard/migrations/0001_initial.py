# Generated by Django 4.2.4 on 2023-10-19 18:38

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('solicitudes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eco_unidad', models.CharField(max_length=50, null=True, unique=True)),
                ('serie', models.CharField(max_length=20, null=True)),
                ('cuenta_contable', models.CharField(max_length=20, null=True)),
                ('factura_interna', models.CharField(max_length=20, null=True)),
                ('descripcion', models.CharField(max_length=100, null=True)),
                ('modelo', models.CharField(blank=True, max_length=30, null=True)),
                ('comentario', models.CharField(max_length=100, null=True)),
                ('completo', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='ArticulosOrdenados',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comentario', models.TextField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Familia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=25, null=True, unique=True)),
                ('status', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Inventario_Batch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.FileField(upload_to='product_bash', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=('csv',))])),
                ('uploaded', models.DateField(auto_now_add=True)),
                ('activated', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Products_Batch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.FileField(upload_to='product_bash', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=('csv',))])),
                ('uploaded', models.DateField(auto_now_add=True)),
                ('activated', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Tipo_Activo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Tipo_Orden',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(max_length=15, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Unidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=10, null=True, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Subfamilia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=30, null=True)),
                ('familia', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.familia')),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=6, null=True, unique=True)),
                ('nombre', models.CharField(max_length=400, null=True)),
                ('especialista', models.BooleanField(default=False)),
                ('iva', models.BooleanField(default=True)),
                ('activo', models.BooleanField(default=False)),
                ('servicio', models.BooleanField(default=False)),
                ('gasto', models.BooleanField(default=False)),
                ('viatico', models.BooleanField(default=False)),
                ('baja_item', models.BooleanField(default=False)),
                ('image', models.ImageField(blank=True, null=True, upload_to='product_images')),
                ('completado', models.BooleanField(default=False)),
                ('precioref', models.DecimalField(decimal_places=2, max_digits=14, null=True)),
                ('porcentaje', models.DecimalField(decimal_places=2, max_digits=3, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('familia', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.familia')),
                ('subfamilia', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.subfamilia')),
                ('unidad', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.unidad')),
            ],
        ),
        migrations.CreateModel(
            name='Plantilla',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('comentario', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateField(auto_now=True)),
                ('complete', models.BooleanField(default=False)),
                ('creador', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Creador', to='user.profile')),
                ('modified_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.profile')),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folio', models.CharField(max_length=6, null=True)),
                ('last_folio_number', models.IntegerField(null=True)),
                ('requisitar', models.BooleanField(default=False, null=True)),
                ('requisitado', models.BooleanField(default=False, null=True)),
                ('complete', models.BooleanField(null=True)),
                ('autorizar', models.BooleanField(default=None, null=True)),
                ('created_at', models.DateField(null=True)),
                ('created_at_time', models.TimeField(null=True)),
                ('approved_at', models.DateField(null=True)),
                ('approved_at_time', models.TimeField(null=True)),
                ('comentario', models.TextField(blank=True, max_length=200, null=True)),
                ('soporte', models.FileField(blank=True, null=True, upload_to='facturas', validators=[django.core.validators.FileExtensionValidator(['pdf'])])),
                ('activo', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.activo')),
                ('distrito', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.distrito')),
                ('operacion', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='solicitudes.operacion')),
                ('proyecto', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='solicitudes.proyecto')),
                ('sector', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='solicitudes.sector')),
                ('staff', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Crea', to='user.profile')),
                ('subproyecto', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='solicitudes.subproyecto')),
                ('superintendente', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='intendente', to='user.profile')),
                ('supervisor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='supervisor', to='user.profile')),
                ('tipo', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.tipo_orden')),
            ],
        ),
        migrations.CreateModel(
            name='Marca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=20, null=True, unique=True)),
                ('familia', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.familia')),
            ],
        ),
        migrations.CreateModel(
            name='Inventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ubicacion', models.CharField(blank=True, max_length=50, null=True)),
                ('estante', models.CharField(blank=True, max_length=30, null=True)),
                ('cantidad', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('cantidad_apartada', models.DecimalField(decimal_places=2, max_digits=14, null=True)),
                ('cantidad_entradas', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('minimo', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('complete', models.BooleanField(default=False)),
                ('comentario', models.CharField(blank=True, max_length=100, null=True)),
                ('activo_disponible', models.BooleanField(default=False)),
                ('almacen', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.almacen')),
                ('distrito', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.distrito')),
                ('marca', models.ManyToManyField(blank=True, to='dashboard.marca')),
                ('producto', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.product')),
            ],
            options={
                'unique_together': {('producto', 'distrito')},
            },
        ),
        migrations.CreateModel(
            name='HistoricalProduct',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('codigo', models.CharField(db_index=True, max_length=6, null=True)),
                ('nombre', models.CharField(max_length=400, null=True)),
                ('especialista', models.BooleanField(default=False)),
                ('iva', models.BooleanField(default=True)),
                ('activo', models.BooleanField(default=False)),
                ('servicio', models.BooleanField(default=False)),
                ('gasto', models.BooleanField(default=False)),
                ('viatico', models.BooleanField(default=False)),
                ('baja_item', models.BooleanField(default=False)),
                ('image', models.TextField(blank=True, max_length=100, null=True)),
                ('completado', models.BooleanField(default=False)),
                ('precioref', models.DecimalField(decimal_places=2, max_digits=14, null=True)),
                ('porcentaje', models.DecimalField(decimal_places=2, max_digits=3, null=True)),
                ('created_at', models.DateTimeField(blank=True, editable=False)),
                ('updated_at', models.DateTimeField(blank=True, editable=False)),
                ('history_change_reason', models.TextField(null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('familia', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='dashboard.familia')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('subfamilia', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='dashboard.subfamilia')),
                ('unidad', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='dashboard.unidad')),
            ],
            options={
                'verbose_name': 'historical product',
                'verbose_name_plural': 'historical products',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalOrder',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('folio', models.CharField(max_length=6, null=True)),
                ('last_folio_number', models.IntegerField(null=True)),
                ('requisitar', models.BooleanField(default=False, null=True)),
                ('requisitado', models.BooleanField(default=False, null=True)),
                ('complete', models.BooleanField(null=True)),
                ('autorizar', models.BooleanField(default=None, null=True)),
                ('created_at', models.DateField(null=True)),
                ('created_at_time', models.TimeField(null=True)),
                ('approved_at', models.DateField(null=True)),
                ('approved_at_time', models.TimeField(null=True)),
                ('comentario', models.TextField(blank=True, max_length=200, null=True)),
                ('soporte', models.TextField(blank=True, max_length=100, null=True, validators=[django.core.validators.FileExtensionValidator(['pdf'])])),
                ('history_change_reason', models.TextField(null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('activo', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='dashboard.activo')),
                ('distrito', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='user.distrito')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('operacion', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='solicitudes.operacion')),
                ('proyecto', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='solicitudes.proyecto')),
                ('sector', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='solicitudes.sector')),
                ('staff', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='user.profile')),
                ('subproyecto', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='solicitudes.subproyecto')),
                ('superintendente', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='user.profile')),
                ('supervisor', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='user.profile')),
                ('tipo', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='dashboard.tipo_orden')),
            ],
            options={
                'verbose_name': 'historical order',
                'verbose_name_plural': 'historical orders',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalInventario',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('ubicacion', models.CharField(blank=True, max_length=50, null=True)),
                ('estante', models.CharField(blank=True, max_length=30, null=True)),
                ('cantidad', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('cantidad_apartada', models.DecimalField(decimal_places=2, max_digits=14, null=True)),
                ('cantidad_entradas', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('minimo', models.PositiveIntegerField(default=0)),
                ('history_change_reason', models.TextField(null=True)),
                ('created_at', models.DateTimeField(blank=True, editable=False)),
                ('updated_at', models.DateTimeField(blank=True, editable=False)),
                ('complete', models.BooleanField(default=False)),
                ('comentario', models.CharField(blank=True, max_length=100, null=True)),
                ('activo_disponible', models.BooleanField(default=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('almacen', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='user.almacen')),
                ('distrito', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='user.distrito')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('producto', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='dashboard.product')),
            ],
            options={
                'verbose_name': 'historical inventario',
                'verbose_name_plural': 'historical inventarios',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalArticulosparaSurtir',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('cantidad', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('precio', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('surtir', models.BooleanField(default=False)),
                ('cantidad_requisitar', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('comentario', models.CharField(blank=True, max_length=60, null=True)),
                ('requisitar', models.BooleanField(default=False, null=True)),
                ('salida', models.BooleanField(default=False, null=True)),
                ('history_change_reason', models.TextField(null=True)),
                ('seleccionado', models.BooleanField(default=False, null=True)),
                ('created_at', models.DateField(blank=True, editable=False)),
                ('created_at_time', models.TimeField(blank=True, editable=False)),
                ('modified_at', models.DateField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('articulos', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='dashboard.articulosordenados')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical articulospara surtir',
                'verbose_name_plural': 'historical articulospara surtirs',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='ArticulosparaSurtir',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('precio', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('surtir', models.BooleanField(default=False)),
                ('cantidad_requisitar', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('comentario', models.CharField(blank=True, max_length=60, null=True)),
                ('requisitar', models.BooleanField(default=False, null=True)),
                ('salida', models.BooleanField(default=False, null=True)),
                ('seleccionado', models.BooleanField(default=False, null=True)),
                ('created_at', models.DateField(auto_now_add=True)),
                ('created_at_time', models.TimeField(auto_now_add=True)),
                ('modified_at', models.DateField(auto_now=True)),
                ('articulos', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.articulosordenados')),
            ],
        ),
        migrations.AddField(
            model_name='articulosordenados',
            name='orden',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.order'),
        ),
        migrations.AddField(
            model_name='articulosordenados',
            name='producto',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.inventario'),
        ),
        migrations.CreateModel(
            name='ArticuloPlantilla',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('comentario_articulo', models.TextField(blank=True, null=True)),
                ('comentario_plantilla', models.TextField(blank=True, null=True)),
                ('modified_at', models.DateField(auto_now=True)),
                ('modified_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.profile')),
                ('plantilla', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.plantilla')),
                ('producto', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.inventario')),
            ],
        ),
        migrations.AddField(
            model_name='activo',
            name='activo',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.inventario'),
        ),
        migrations.AddField(
            model_name='activo',
            name='creado_por',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Creado_por', to='user.profile'),
        ),
        migrations.AddField(
            model_name='activo',
            name='marca',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.marca'),
        ),
        migrations.AddField(
            model_name='activo',
            name='responsable',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.profile'),
        ),
        migrations.AddField(
            model_name='activo',
            name='tipo_activo',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.tipo_activo'),
        ),
    ]
