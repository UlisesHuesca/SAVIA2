
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from boveda_xml.models import CFDI
from tesoreria.views import consultar_estatus_sat


class Command(BaseCommand):

    help = "Actualiza el estado fiscal de los CFDI ante el SAT."

    def add_arguments(self, parser):
        parser.add_argument("--desde", type=str, help="Fecha inicial YYYY-MM-DD")

        parser.add_argument("--hasta", type=str, help="Fecha final YYYY-MM-DD")

    def handle(self, *args, **options):

        fecha_limite = timezone.now() - timedelta(hours=4)

        # CFDI que nunca se han validado o cuya última
        # validación ocurrió hace al menos cuatro horas.
        cfdis = CFDI.objects.filter(Q(fecha_validacion_sat__isnull=True)| Q(fecha_validacion_sat__lte=fecha_limite)
        ).exclude(
            uuid__isnull=True
        ).exclude(
            uuid=""
        )

        # Rango opcional para ejecuciones manuales.
        desde = options["desde"]
        hasta = options["hasta"]

        if bool(desde) != bool(hasta):
            raise CommandError(
                "Debes proporcionar --desde y --hasta juntos."
            )

        if desde and hasta:
            fecha_inicio = parse_date(desde)
            fecha_fin = parse_date(hasta)

            if (fecha_inicio is None or fecha_fin is None or fecha_inicio > fecha_fin):
                raise CommandError("El rango de fechas no es válido.")

            zona = timezone.get_current_timezone()

            inicio = timezone.make_aware(datetime.combine(fecha_inicio, time.min), zona)

            fin_exclusivo = timezone.make_aware(datetime.combine(fecha_fin + timedelta(days=1), time.min), zona)

            cfdis = cfdis.filter(fecha_timbrado__gte=inicio, fecha_timbrado__lt=fin_exclusivo)

        # Sin límite de 10 registros.
        cfdis = cfdis.order_by("fecha_validacion_sat", "pk")

        total = cfdis.count()

        resultados = {
            "vigentes": 0,
            "cancelados": 0,
            "no_encontrados": 0,
            "errores": 0,
        }

        self.stdout.write(f"Iniciando validación SAT. CFDI elegibles: {total}")

        for cfdi in cfdis.iterator(chunk_size=100):

            if (not cfdi.rfc_emisor or not cfdi.rfc_receptor or cfdi.total is None):
                resultados["errores"] += 1
                continue

            try:
                estado = consultar_estatus_sat(
                    rfc_emisor=cfdi.rfc_emisor,
                    rfc_receptor=cfdi.rfc_receptor,
                    total=cfdi.total,
                    uuid=str(cfdi.uuid)
                )

                estado_normalizado = ((estado or "").strip().upper())

                if estado_normalizado == "VIGENTE":
                    resultados["vigentes"] += 1

                elif estado_normalizado == "CANCELADO":
                    resultados["cancelados"] += 1

                elif estado_normalizado == "NO ENCONTRADO":
                    resultados["no_encontrados"] += 1

                else:
                    resultados["errores"] += 1
                    self.stderr.write(
                        f"SAT sin resultado válido "
                        f"UUID={cfdi.uuid}: {estado}"
                    )
                    continue

                cfdi.estado_sat = estado_normalizado
                cfdi.fecha_validacion_sat = timezone.now()

                cfdi.save(update_fields=["estado_sat", "fecha_validacion_sat",])

            except Exception as error:
                resultados["errores"] += 1
                self.stderr.write(f"Error UUID={cfdi.uuid}: {error}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Validación terminada. "
                f"Vigentes: {resultados['vigentes']}, "
                f"Cancelados: {resultados['cancelados']}, "
                f"No encontrados: {resultados['no_encontrados']}, "
                f"Errores: {resultados['errores']}."
            )
        )
