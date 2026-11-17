
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dashboard.models import (
    Product,
    ProductoTerminado,
    ComponenteProductoTerminado,
)


# ============================================================
# MATERIALES DE PRUEBA - PEDESTAL DE 144"
# Código VORDCAB: P + código VORDTEC con 5 dígitos
# ============================================================

MATERIALES = [
    ("2703", "PLACA 1 PULG ESP X 14 3/4 ANCHO X 14 3/4 LONG ASTM A36", "3.00"),
    ("689", "PTR 2 1/2 X 2 1/2 X 3/16 A36", "7.00"),
    ("1458", "PTR 2 X 2 X 3/16 A36", "0.50"),
    ("70", "ANGULO 2 X 1/4 A36", "0.33"),
    ("5238", "PLACA 1/2 X 3FT X 10FT A36", "0.25"),
    ("72", "PLACA 3/8 X 3FT X 8FT A36", "0.25"),
    ("399", "COPLE ROSCADO 2 7/8 #3000", "1.00"),
    ("139", "TORNILLO HEX 3/8 X 1 1/2 GALV G5", "1.00"),
    ("10376", "TORNILLO HEXAGONAL 1 X 6 GALV G5", "4.00"),
    ("167", "ARANDELA PLANA 1 GALV", "4.00"),
    ("133", "RONDANA DE PRESION GALV 1", "4.00"),
    ("1298", "TUERCA HEX 1 GALV", "4.00"),
    ("171", "TORNILLO HEX 1/2 X 2 GALV G5", "2.00"),
    ("1186", "TORNILLO HEX 1/2 X 2 1/2 GALV G5", "4.00"),
    ("106", "RONDANA DE PRESION 1/2 GALV", "4.00"),
    ("108", "TUERCA HEX 1/2 GALV", "10.00"),
    ("117", "ARANDELA PLANA 1/2 GALV", "6.00"),
    ("2707", "BARRA HUECA AISI 1018 2 EXT X 1 INT X 15 LONG", "1.00"),
    ("10295", "REDONDO 1 1/8 ASTM A36", "0.11"),
    ("8200", "CUBETA DE RECUBRIMIENTO RA-28 NEGRO", "0.50"),
    ("7687", "CUBETA DE PRIMARIO RP-06 ROJO", "0.25"),
    ("2233", "THINNER ESTANDAR", "10.00"),
    ("4107", "THINNER ACRILICO", "15.00"),
    ("99", "TRAPO INDUSTRIAL", "5.00"),
]


class Command(BaseCommand):

    help = (
        "Carga los materiales y la composición BOM "
        "de prueba del pedestal de 144 pulgadas."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--database",
            default="default",
            help="Alias de la base de datos donde se ejecutará la carga.",
        )

        parser.add_argument(
            "--confirmar-cantidades",
            action="store_true",
            help="Registra o actualiza los materiales de la BOM.",
        )

    def handle(self, *args, **options):

        # Utilizar la conexión indicada mediante --database.
        database = options["database"]

        try:
            with transaction.atomic(using=database):

                # ============================================
                # 1. CREAR O VERIFICAR MATERIALES
                # ============================================

                materiales = []

                for codigo_origen, nombre, cantidad in MATERIALES:

                    codigo = f"P{codigo_origen.zfill(5)}"

                    if len(codigo) > 6:
                        raise CommandError(
                            f"El código {codigo} excede 6 caracteres."
                        )

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

                    if producto.nombre != nombre:
                        raise CommandError(
                            f"Conflicto con el código {codigo}. "
                            f"Nombre existente: {producto.nombre}"
                        )

                    materiales.append(
                        (producto, Decimal(cantidad))
                    )

                    self.stdout.write(
                        f"{'CREADO' if creado else 'EXISTENTE'}: "
                        f"{codigo} - {nombre}"
                    )

                # ============================================
                # 2. CREAR PRODUCTO CONCEPTUAL
                # ============================================

                producto_padre, creado = (
                    Product.objects.using(database).get_or_create(
                        codigo="PT0001",
                        defaults={
                            "nombre": 'PEDESTAL DE 144"',
                            "activo": True,
                            "completado": False,
                        },
                    )
                )

                if producto_padre.nombre != 'PEDESTAL DE 144"':
                    raise CommandError(
                        "El código PT0001 pertenece a otro producto."
                    )

                self.stdout.write(
                    f"{'CREADO' if creado else 'EXISTENTE'}: "
                    'PT0001 - PEDESTAL DE 144"'
                )

                # ============================================
                # 3. CREAR EXTENSIÓN PRODUCTO TERMINADO
                # ============================================

                pedestal, creado = (
                    ProductoTerminado.objects.using(database).get_or_create(
                        producto=producto_padre,
                        defaults={
                            "tipo": ProductoTerminado.Tipo.SUBCOMPONENTE,
                            "descripcion_fabricacion": (
                                "Fabricación de pedestal de 144 pulgadas."
                            ),
                            "activo": True,
                        },
                    )
                )

                if pedestal.tipo != ProductoTerminado.Tipo.SUBCOMPONENTE:
                    raise CommandError(
                        "PT0001 ya existe como producto terminado "
                        "con un tipo diferente a SUBCOMPONENTE."
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        "Producto terminado PT0001 verificado."
                    )
                )

                # ============================================
                # 4. REGISTRAR COMPOSICIÓN BOM
                # ============================================

                if not options["confirmar_cantidades"]:
                    self.stdout.write(
                        self.style.WARNING(
                            "Materiales y pedestal registrados. "
                            "La BOM todavía no se ha creado."
                        )
                    )
                    return

                creados = 0
                actualizados = 0

                for material, cantidad in materiales:

                    componente, creado = (
                        ComponenteProductoTerminado.objects.using(
                            database
                        ).update_or_create(
                            producto_padre=pedestal,
                            material=material,
                            producto_hijo=None,
                            defaults={
                                "cantidad": cantidad,
                                "comentario": (
                                    "BOM de prueba - Pedestal de 144 pulgadas"
                                ),
                            },
                        )
                    )

                    if creado:
                        creados += 1
                    else:
                        actualizados += 1

                    self.stdout.write(
                        f"{'AGREGADO' if creado else 'ACTUALIZADO'}: "
                        f"{material.codigo} - Cantidad: {cantidad}"
                    )

                # ============================================
                # 5. RESUMEN
                # ============================================

                total = (
                    ComponenteProductoTerminado.objects.using(database)
                    .filter(producto_padre=pedestal)
                    .count()
                )

                self.stdout.write("")
                self.stdout.write(
                    self.style.SUCCESS(
                        "BOM del pedestal registrada correctamente."
                    )
                )
                self.stdout.write(
                    f'Producto: PT0001 - PEDESTAL DE 144"'
                )
                self.stdout.write(
                    f"Tipo: {pedestal.get_tipo_display()}"
                )
                self.stdout.write(f"Materiales agregados: {creados}")
                self.stdout.write(f"Materiales actualizados: {actualizados}")
                self.stdout.write(f"Total de elementos BOM: {total}")
                self.stdout.write(f"Base de datos: {database}")

        except CommandError:
            raise

        except Exception as exc:
            raise CommandError(
                f"No fue posible completar la carga: {exc}"
            ) from exc
