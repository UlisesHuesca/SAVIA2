# Generated by Django 4.2.4 on 2023-10-23 17:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
        ('gastos', '0002_remove_articulo_gasto_entrada_salida_express_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='solicitud_gasto',
            old_name='area',
            new_name='operacion',
        ),
        migrations.AddField(
            model_name='solicitud_gasto',
            name='distrito',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='user.distrito'),
        ),
        migrations.AlterField(
            model_name='solicitud_gasto',
            name='folio',
            field=models.CharField(max_length=6, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='solicitud_gasto',
            unique_together={('folio', 'distrito')},
        ),
    ]
