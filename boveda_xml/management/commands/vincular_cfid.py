
from itertools import islice

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from boveda_xml.models import CFDI
from tesoreria.models import Facturas
from gastos.models import Factura
from viaticos.models import Viaticos_Factura


def normalizar_uuid(valor):
    return str(valor or "").strip().upper()


def obtener_lotes(iterable, tamano=500):
    while True:
        lote = list(islice(iterable, tamano))
        if not lote:
            break
        yield lote


class Command(BaseCommand):

    help = "Vincula CFDI históricos con Compras, Gastos y Viáticos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Mostrar resultados sin guardar relaciones."
        )

    def handle(self, *args, **options):

        simular = options["simular"]

        resultados = {
            "revisados": 0,
            "compras": 0,
            "gastos": 0,
            "viaticos": 0,
            "sin_coincidencia": 0,
            "conflictos": 0,
            "omitidos": 0,
            "errores": 0,
        }

        # Solamente CFDI sin ninguna relación.
        pendientes = (
            CFDI.objects
            .filter(
                factura_compra__isnull=True,
                factura_gasto__isnull=True,
                factura_viatico__isnull=True,
            )
            .exclude(uuid__isnull=True)
            .exclude(uuid="")
            .order_by("pk")
            .values_list("pk", "uuid")
        )

        total = pendientes.count()

        self.stdout.write(
            f"CFDI pendientes por revisar: {total}"
        )

        if simular:
            self.stdout.write(
                self.style.WARNING(
                    "MODO SIMULACIÓN: No se guardarán cambios."
                )
            )

        # Evitar cargar toda la Bóveda en memoria.
        registros = pendientes.iterator(chunk_size=500)

        for lote in obtener_lotes(registros, 500):

            uuids = list({
                normalizar_uuid(uuid)
                for _, uuid in lote
                if normalizar_uuid(uuid)
            })

            # Consultar cada módulo por separado.
            modelos = [
                ("compras", "factura_compra", Facturas),
                ("gastos", "factura_gasto", Factura),
                ("viaticos", "factura_viatico", Viaticos_Factura),
            ]

            coincidencias = {}

            for modulo, campo, modelo in modelos:

                facturas = modelo.objects.filter(
                    uuid__in=uuids
                ).values_list("pk", "uuid")

                for factura_id, uuid_factura in facturas:

                    uuid_normalizado = normalizar_uuid(
                        uuid_factura
                    )

                    coincidencias.setdefault(
                        uuid_normalizado, []
                    ).append(
                        (modulo, campo, factura_id)
                    )

            # Procesar cada CFDI del lote.
            for cfdi_id, uuid in lote:

                resultados["revisados"] += 1

                uuid_normalizado = normalizar_uuid(uuid)

                encontrados = coincidencias.get(
                    uuid_normalizado, []
                )

                if not encontrados:
                    resultados["sin_coincidencia"] += 1
                    continue

                # Un UUID registrado más de una vez
                # requiere revisión manual.
                if len(encontrados) != 1:

                    resultados["conflictos"] += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"CONFLICTO UUID={uuid}: "
                            f"{len(encontrados)} coincidencias."
                        )
                    )
                    continue

                modulo, campo, factura_id = encontrados[0]

                try:
                    with transaction.atomic():

                        # Bloquear registro y comprobar
                        # nuevamente que continúa disponible.
                        cfdi = (
                            CFDI.objects
                            .select_for_update()
                            .get(pk=cfdi_id)
                        )

                        if (
                            cfdi.factura_compra_id is not None
                            or cfdi.factura_gasto_id is not None
                            or cfdi.factura_viatico_id is not None
                        ):
                            resultados["omitidos"] += 1
                            continue

                        # No utilizar una factura que ya
                        # esté vinculada a otro CFDI.
                        factura_ocupada = (
                            CFDI.objects
                            .filter(**{campo: factura_id})
                            .exclude(pk=cfdi.pk)
                            .exists()
                        )

                        if factura_ocupada:
                            resultados["conflictos"] += 1

                            self.stdout.write(
                                self.style.WARNING(
                                    f"Factura ocupada: UUID={uuid}"
                                )
                            )
                            continue

                        if not simular:
                            setattr(
                                cfdi,
                                f"{campo}_id",
                                factura_id
                            )

                            cfdi.save(
                                update_fields=[campo]
                            )

                    resultados[modulo] += 1

                except (IntegrityError, Exception) as error:
                    resultados["errores"] += 1

                    self.stderr.write(
                        f"ERROR UUID={uuid}: {error}"
                    )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "========== RESULTADO VINCULACIÓN =========="
            )
        )

        for clave, cantidad in resultados.items():
            self.stdout.write(
                f"{clave}: {cantidad}"
            )

        self.stdout.write(
            "==========================================="
        )
