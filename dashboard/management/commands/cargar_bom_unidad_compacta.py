
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.models import (
    Product,
    ProductoTerminado,
    ComponenteProductoTerminado,
)


# ============================================================
# MATERIALES DEL DEPÓSITO DE ACEITE
# Código original VORDTEC, descripción y cantidad
# ============================================================

MATERIALES_DEPOSITO = [
    ("3657", "TAPON RESPIRADERO METALICO SS-52-01 COD 21 VC-050", "1.00"),
    ("201", "FILTRO DONALDSON K070249", "1.00"),
    ("2115", 'ANGULO 3" X 3/16" X 6M ASTM A36', "1.00"),
    ("7872", 'CEDAZO DE SUCCION FILTRO VESCOR 21-VC-106/SS100 NPT Ø 3"', "1.00"),
    ("1230", 'NIPLE 3" X 5"', "1.00"),
    ("337", 'TAPON MACHO 2" NPT #150', "1.00"),
    ("721", 'TORNILLO HEX ACERO AL CARBON 1/2" X 1 1/2"', "8.00"),
    ("108", 'TUERCA HEX 1/2 GALV', "18.00"),
    ("117", 'ARANDELA PLANA 1/2 GALV', "26.00"),
    ("76", 'ANGULO 2" X 3/16"', "11.00"),
    ("240", 'MD COPLE ROSCADO 2" #3000', "1.00"),
    ("395", 'MD COPLE ROSCADO 1/2" #3000', "2.00"),
    ("344", 'MD COPLE ROSCADO 3/8" #3000', "2.00"),
    ("345", 'MD COPLE ROSCADO 3/4" #3000', "1.00"),
]


class Command(BaseCommand):

    help = (
        "Carga la BOM de prueba del Depósito de Aceite "
        "y la Unidad Compacta de 144 pulgadas."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--database",
            default="default",
            help="Alias de la base de datos destino.",
        )

        parser.add_argument(
            "--confirmar-cantidades",
            action="store_true",
            help="Confirma y registra las cantidades BOM.",
        )

    @transaction.atomic
    def handle(self, *args, **options):

        database = options["database"]
        confirmar = options["confirmar_cantidades"]

        if database != "default":
            raise CommandError(
                "Este comando solamente puede ejecutarse "
                "en la base de datos default (VORDCAB)."
            )

        # ----------------------------------------------------
        # 1. Verificar pedestal existente
        # ----------------------------------------------------

        pedestal = (
            ProductoTerminado.objects.using(database)
            .select_related("producto")
            .filter(producto__codigo="PT0001")
            .first()
        )

        if not pedestal:
            raise CommandError(
                "No existe PT0001. Ejecuta primero "
                "la carga de la BOM del pedestal."
            )

        # ----------------------------------------------------
        # 2. Preparar los materiales del depósito
        # ----------------------------------------------------

        materiales = []

        for codigo_origen, nombre, cantidad in MATERIALES_DEPOSITO:

            codigo = f"P{codigo_origen.zfill(5)}"

            producto, creado = (
                Product.objects.using(database).get_or_create(
                    codigo=codigo,
                    defaults={
                        "nombre": nombre,
                        "activo": True,
                        "completado": False,
                    },
                )
            )

            materiales.append(
                (producto, Decimal(cantidad))
            )

            self.stdout.write(
                f"{'CREADO' if creado else 'EXISTENTE'}: "
                f"{codigo} - {producto.nombre}"
            )

        # ----------------------------------------------------
        # 3. Crear producto conceptual del depósito
        # ----------------------------------------------------

        producto_deposito, creado = (
            Product.objects.using(database).get_or_create(
                codigo="PT0002",
                defaults={
                    "nombre": "DEPOSITO DE ACEITE",
                    "activo": True,
                    "completado": False,
                },
            )
        )

        deposito, creado = (
            ProductoTerminado.objects.using(database).get_or_create(
                producto=producto_deposito,
                defaults={
                    "tipo": ProductoTerminado.Tipo.SUBCOMPONENTE,
                    "descripcion_fabricacion": (
                        'Depósito de aceite de la '
                        'Unidad Compacta de 144 pulgadas.'
                    ),
                    "activo": True,
                },
            )
        )

        self.stdout.write(
            f"\nDepósito PT0002 "
            f"{'creado' if creado else 'verificado'}."
        )

        # ----------------------------------------------------
        # 4. Crear producto conceptual del equipo
        # ----------------------------------------------------

        producto_equipo, creado = (
            Product.objects.using(database).get_or_create(
                codigo="PT0003",
                defaults={
                    "nombre": 'UNIDAD COMPACTA DE 144"',
                    "activo": True,
                    "completado": False,
                },
            )
        )

        equipo, creado = (
            ProductoTerminado.objects.using(database).get_or_create(
                producto=producto_equipo,
                defaults={
                    "tipo": ProductoTerminado.Tipo.EQUIPO,
                    "descripcion_fabricacion": (
                        'Equipo Unidad Compacta de 144 pulgadas.'
                    ),
                    "activo": True,
                },
            )
        )

        self.stdout.write(
            f"Equipo PT0003 "
            f"{'creado' if creado else 'verificado'}."
        )

        # ----------------------------------------------------
        # 5. Registrar BOM del depósito
        # ----------------------------------------------------

        if not confirmar:

            self.stdout.write(
                self.style.WARNING(
                    "\nSe crearon o verificaron los productos. "
                    "Las relaciones BOM todavía no se registraron."
                )
            )
            return

        total_materiales = 0

        for material, cantidad in materiales:

            componente, creado = (
                ComponenteProductoTerminado.objects.using(database)
                .get_or_create(
                    producto_padre=deposito,
                    material=material,
                    defaults={
                        "cantidad": cantidad,
                    },
                )
            )

            if creado:
                componente.full_clean()
            elif componente.cantidad != cantidad:
                componente.cantidad = cantidad
                componente.full_clean()
                componente.save(using=database, update_fields=["cantidad"])

            total_materiales += 1

            self.stdout.write(
                f"{'AGREGADO' if creado else 'VERIFICADO'}: "
                f"{material.codigo} - Cantidad: {cantidad}"
            )

        # ----------------------------------------------------
        # 6. Vincular subcomponentes al equipo
        # ----------------------------------------------------

        for subcomponente in [pedestal, deposito]:

            relacion, creado = (
                ComponenteProductoTerminado.objects.using(database)
                .get_or_create(
                    producto_padre=equipo,
                    producto_hijo=subcomponente,
                    defaults={
                        "cantidad": Decimal("1.0000"),
                    },
                )
            )

            self.stdout.write(
                f"{'VINCULADO' if creado else 'EXISTENTE'}: "
                f"{equipo.producto.codigo} -> "
                f"{subcomponente.producto.codigo}"
            )

        # ----------------------------------------------------
        # 7. Resumen
        # ----------------------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                "\nBOM multinivel registrada correctamente.\n"
                f"Equipo: {equipo.producto.codigo}\n"
                f"Subcomponentes: 2\n"
                f"Materiales del depósito: {total_materiales}"
            )
        )
