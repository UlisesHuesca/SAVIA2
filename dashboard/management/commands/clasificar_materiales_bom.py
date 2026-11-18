
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.models import Product, Familia


CLASIFICACION = {
    "Estructural": [
        "P00070", "P00072", "P00076",
        "P00689", "P01458", "P02115",
        "P02703", "P05238", "P10295",
    ],
    "Consumible": [
        "P00099", "P02233", "P04107",
    ],
    "Tornillería": [
        "P00106", "P00108", "P00117",
        "P00133", "P00139", "P00167",
        "P00171", "P00721", "P01186",
        "P01298", "P10376",
    ],
    "Accesorios": [
        "P00201",
    ],
    "Hidráulico": [
        "P00240", "P00337", "P00344",
        "P00345", "P00395", "P00399",
        "P01230", "P03657", "P07872",
    ],
    "Material para fabricación": [
        "P02707",
    ],
    "Recubrimiento": [
        "P07687", "P08200",
    ],
}


class Command(BaseCommand):

    help = "Clasifica los materiales de prueba de MIG-002 por familia."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="default",
        )

        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Aplica los cambios en la base de datos.",
        )

    def handle(self, *args, **options):

        database = options["database"]
        confirmar = options["confirmar"]

        if database != "default":
            raise CommandError(
                "Solo se permite la base default de VORDCAB."
            )

        codigos = [
            codigo
            for lista in CLASIFICACION.values()
            for codigo in lista
        ]

        if len(codigos) != len(set(codigos)):
            raise CommandError(
                "Hay códigos duplicados en la clasificación."
            )

        productos = {
            producto.codigo: producto
            for producto in Product.objects.using(database)
            .filter(codigo__in=codigos)
        }

        faltantes = sorted(set(codigos) - set(productos))

        if faltantes:
            raise CommandError(
                "No se encontraron los productos: "
                + ", ".join(faltantes)
            )

        self.stdout.write(
            f"Materiales identificados: {len(productos)}"
        )

        if not confirmar:
            for familia, lista in CLASIFICACION.items():
                self.stdout.write(
                    f"{familia}: {len(lista)} materiales"
                )

            self.stdout.write(
                self.style.WARNING(
                    "Vista previa. No se realizaron cambios. "
                    "Utiliza --confirmar para aplicar."
                )
            )
            return

        with transaction.atomic(using=database):

            for nombre_familia, lista in CLASIFICACION.items():

                # Ajustar 'nombre' si el modelo Familia
                # utiliza otro campo para su denominación.
                familia, creada = (
                    Familia.objects.using(database)
                    .get_or_create(nombre=nombre_familia)
                )

                actualizados = 0

                for codigo in lista:

                    producto = productos[codigo]

                    if producto.familia_id != familia.pk:
                        producto.familia = familia
                        producto.save(
                            using=database,
                            update_fields=["familia", "updated_at"]
                        )
                        actualizados += 1

                self.stdout.write(
                    f"{nombre_familia}: "
                    f"{actualizados} actualizados"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Clasificación de materiales completada."
            )
        )
