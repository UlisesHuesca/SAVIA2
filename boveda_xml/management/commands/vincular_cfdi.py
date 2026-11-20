
from django.core.management.base import BaseCommand
from django.db import transaction

from boveda_xml.models import CFDI
from tesoreria.models import Facturas
from gastos.models import Factura
from viaticos.models import Viaticos_Factura


def normalizar_uuid(valor):
    return str(valor or "").strip().upper()


class Command(BaseCommand):

    help = "Relaciona CFDI de Bóveda con facturas existentes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Identifica relaciones sin modificar la BD.",
        )

    def handle(self, *args, **options):

        simular = options["simular"]
        tamano_lote = 500

        modelos = [
            ("compras", "factura_compra", Facturas, "uuid"),
            ("gastos", "factura_gasto", Factura, "uuid"),
            ("viaticos", "factura_viatico", Viaticos_Factura, "uuid"),
        ]

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

        # --------------------------------------------------
        # 1. Identificar CFDI pendientes
        # --------------------------------------------------

        pendientes = (
            CFDI.objects
            .filter(
                factura_compra__isnull=True,
                factura_gasto__isnull=True,
                factura_viatico__isnull=True,
            )
            .exclude(uuid__isnull=True)
            .exclude(uuid="")
        )

        total_cfdi = CFDI.objects.count()
        total_pendientes = pendientes.count()

        self.stdout.write(
            f"Total CFDI en Bóveda: {total_cfdi}"
        )

        self.stdout.write(
            f"CFDI pendientes de vincular: {total_pendientes}"
        )

        if simular:
            self.stdout.write(
                self.style.WARNING(
                    "MODO SIMULACIÓN - No se guardarán cambios."
                )
            )

        # --------------------------------------------------
        # 2. Procesar todos los CFDI por lotes
        # --------------------------------------------------

        ultimo_id = 0

        while True:

            lote = list(
                pendientes
                .filter(pk__gt=ultimo_id)
                .order_by("pk")
                .values_list("pk", "uuid")[:tamano_lote]
            )

            if not lote:
                break

            ultimo_id = lote[-1][0]

            # UUID que buscaremos en los tres modelos.
            uuids = {
                normalizar_uuid(uuid)
                for _, uuid in lote
                if normalizar_uuid(uuid)
            }

            # Incluimos las representaciones originales
            # para evitar diferencias simples de formato.
            uuids_busqueda = set(uuids)

            for _, uuid in lote:
                if uuid:
                    uuids_busqueda.add(str(uuid).strip())

            # ------------------------------------------------
            # 3. Buscar facturas existentes
            # ------------------------------------------------

            coincidencias = {}

            for modulo, campo, modelo, campo_uuid in modelos:

                facturas = (
                    modelo.objects
                    .filter(**{
                        f"{campo_uuid}__in": uuids_busqueda
                    })
                    .values_list("pk", campo_uuid)
                )

                for factura_id, uuid_factura in facturas:

                    uuid_normalizado = normalizar_uuid(
                        uuid_factura
                    )

                    coincidencias.setdefault(
                        uuid_normalizado, []
                    ).append(
                        (modulo, campo, factura_id)
                    )

            # ------------------------------------------------
            # 4. Vincular CFDI
            # ------------------------------------------------

            for cfdi_id, uuid in lote:

                resultados["revisados"] += 1

                encontrados = coincidencias.get(
                    normalizar_uuid(uuid), []
                )

                if not encontrados:
                    resultados["sin_coincidencia"] += 1
                    continue

                if len(encontrados) > 1:

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

                        # Bloqueo del CFDI para evitar
                        # dos vinculaciones simultáneas.
                        cfdi = (
                            CFDI.objects
                            .select_for_update()
                            .get(pk=cfdi_id)
                        )

                        # Revalidar las tres relaciones.
                        if (
                            cfdi.factura_compra_id is not None
                            or cfdi.factura_gasto_id is not None
                            or cfdi.factura_viatico_id is not None
                        ):
                            resultados["omitidos"] += 1
                            continue

                        # Verificar que la factura no esté
                        # vinculada con otro CFDI.
                        ocupada = (
                            CFDI.objects
                            .filter(**{campo: factura_id})
                            .exclude(pk=cfdi.pk)
                            .exists()
                        )

                        if ocupada:

                            resultados["conflictos"] += 1

                            self.stdout.write(
                                self.style.WARNING(
                                    f"Factura ya ocupada: "
                                    f"UUID={uuid}"
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

                except Exception as error:

                    resultados["errores"] += 1

                    self.stderr.write(
                        f"ERROR UUID={uuid}: {error}"
                    )

        # --------------------------------------------------
        # 5. Resumen final
        # --------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "======= VINCULACIÓN CFDI ======="
            )
        )

        self.stdout.write(
            f"Revisados: {resultados['revisados']}"
        )

        self.stdout.write(
            f"Compras: {resultados['compras']}"
        )

        self.stdout.write(
            f"Gastos: {resultados['gastos']}"
        )

        self.stdout.write(
            f"Viáticos: {resultados['viaticos']}"
        )

        self.stdout.write(
            f"Sin coincidencia: {resultados['sin_coincidencia']}"
        )

        self.stdout.write(
            f"Conflictos: {resultados['conflictos']}"
        )

        self.stdout.write(
            f"Omitidos durante ejecución: {resultados['omitidos']}"
        )

        self.stdout.write(
            f"Errores: {resultados['errores']}"
        )

        self.stdout.write(
            "================================"
        )
