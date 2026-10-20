
import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gastos.models import CodigoSATPermitido


class Command(BaseCommand):
    help = "Importar códigos SAT autorizados para viáticos"

    def add_arguments(self, parser):
        parser.add_argument("archivo", type=str)

    
    def handle(self, *args, **options):
        archivo = options["archivo"]

        try:
            with open(archivo, encoding="utf-8-sig", newline="") as f:
                lector = csv.DictReader(f)
                registros = list(lector)

        except (OSError, UnicodeError, csv.Error) as error:
            raise CommandError(str(error))

        creados = 0
        actualizados = 0

        with transaction.atomic():
            for fila in registros:
                codigo = fila["Código SAT"].strip()
                concepto = fila["Concepto SAT"].strip()

                # Importamos los candidatos, pero no concedemos
                # autorización automáticamente.
                objeto, creado = CodigoSATPermitido.objects.update_or_create(
                    codigo=codigo,
                    defaults={
                        "concepto": concepto,
                    }
                )

                if creado:
                    creados += 1
                else:
                    actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Importación finalizada. "
                f"Creados: {creados}. "
                f"Actualizados: {actualizados}."
            )
        )
