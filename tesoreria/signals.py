# tesoreria/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pago, Saldo_Cuenta

@receiver(post_save, sender=Pago)
def actualizar_saldos(sender, instance, created, **kwargs):
    # Evitar recursión infinita
    if hasattr(instance, '_avoid_signal'):
        return
    
    # Asegurarse de que la cuenta y la fecha no sean None
    if not instance.cuenta or not instance.pagado_real:
        return

    # Obtener el saldo inicial o crear uno si no existe
    latest_balance_record = Saldo_Cuenta.objects.filter(cuenta=instance.cuenta).order_by('-fecha_inicial').first()
    if not latest_balance_record:
        saldo_inicial = 0
        Saldo_Cuenta.objects.create(cuenta=instance.cuenta, monto_inicial=saldo_inicial, fecha_inicial=instance.pagado_real)
    else:
        saldo_inicial = latest_balance_record.monto_inicial
    print(saldo_inicial)
    # Obtener todos los pagos posteriores al nuevo pago y actualizar los saldos
    if latest_balance_record != None:
        pagos_posteriores = Pago.objects.filter(
            cuenta=instance.cuenta,
            hecho= True,
            pagado_real__gte = latest_balance_record.fecha_inicial
        ).order_by('pagado_real')
        saldo_acumulado = latest_balance_record.monto_inicial
        index = 0
        for pago in pagos_posteriores:
            if pago.tipo and pago.tipo.nombre == "ABONO":
                saldo_acumulado += pago.monto
            else:
                saldo_acumulado -= pago.monto
            print('pagado_real:',pago.pagado_real,'pago_monto:',pago.monto,'saldo_acumulado:',saldo_acumulado)
            pago.saldo = saldo_acumulado
            index += 1
            pago.indice = index
            # Evitar recursión infinita
            pago._avoid_signal = True
            pago.save()
            del pago._avoid_signal

    # Volver a conectar la señal
    post_save.connect(actualizar_saldos, sender=Pago)
