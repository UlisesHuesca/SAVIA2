# tesoreria/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pago, Saldo_Cuenta

@receiver(post_save, sender=Pago)
def actualizar_saldos(sender, instance, created, **kwargs):
    if created:
        # Obtener el saldo inicial
        latest_balance_record = Saldo_Cuenta.objects.filter(cuenta=instance.cuenta).order_by('-fecha_inicial').first()
        saldo_inicial = latest_balance_record.monto_inicial if latest_balance_record else 0

        # Obtener todos los pagos posteriores al nuevo pago y actualizar los saldos
        pagos_posteriores = Pago.objects.filter(
            cuenta=instance.cuenta,
            pagado_real__gt=instance.pagado_real
        ).order_by('pagado_real')

        for pago in pagos_posteriores:
            if pago.tipo and pago.tipo.nombre == "ABONO":
                saldo_acumulado += pago.monto
            else:
                saldo_acumulado -= pago.monto
            pago.saldo = saldo_acumulado
            pago.save()
