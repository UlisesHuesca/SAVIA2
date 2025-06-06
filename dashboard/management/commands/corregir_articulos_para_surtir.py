from django.core.management.base import BaseCommand
from requisiciones.models import Salidas
#from dashboard.models import ArticulosparaSurtir  # Ajusta el import
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Corrige ArticulosparaSurtir si las salidas completadas coinciden con la cantidad solicitada.'

    def handle(self, *args, **kwargs):
        total_salidas = 0
        modificados = 0
        fecha_inicio = datetime(2024, 1, 1, tzinfo=timezone.utc)
        salidas = Salidas.objects.filter(cancelada=False, complete=True, created_at__gte=fecha_inicio)

        for salida in salidas:
            total_salidas += 1
            articulo = salida.producto #Este es el articulos para surtir relacionado a la salida

            if not articulo or articulo.salida:
                continue  # Ya corregido o producto inválido

            cantidad_requerida = articulo.articulos.cantidad

            total_surtido = Salidas.objects.filter(
                producto=articulo,
                cancelada=False
            ).aggregate(total=Sum('cantidad'))['total'] or Decimal('0')

            if (
                Decimal(total_surtido) == Decimal(cantidad_requerida) and 
                articulo.surtir and 
                not articulo.salida
            ):
                articulo.salida = True
                articulo.surtir = False
                articulo.cantidad = 0
                articulo.save(update_fields=['salida', 'surtir', 'cantidad'])
                modificados += 1
                logger.info(f"Corregido artículo ID={articulo.id} desde salida ID={salida.id} | Total surtido: {total_surtido}")

        self.stdout.write(f"Evaluadas: {total_salidas} salidas completadas.")
        self.stdout.write(f"Artículos corregidos: {modificados}")

