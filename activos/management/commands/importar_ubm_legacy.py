import re
import unicodedata
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction

from activos.models import Bomba_UBM, Manifold_UBM, Motor_UBM, UBM_Activo
from dashboard.models import Activo


VALORES_SIN_DATO = {
    '',
    'N/A',
    'NA',
    'N.A.',
    'NV',
    'N/V',
    'N.V.',
    'NT',
    'N/D',
    'ND',
    'S/D',
    'SD',
    'NO APLICA',
    'SIN INFORMACION',
    'SIN INFORMACIÓN',
    'SIN BOMBA',
    'SIN MOTOR',
    'SIN MANIFOLD',
}


TIPOS_UBM = {
    'UBM 120"': 'UBM_120',
    'UBM 144"': 'UBM_144',
    'UBMC 144"': 'UBM_144',
    'UBMSC 300"': 'UBMSC_300',
    'UBMSC 320"': 'UBMSC_320',
    'UBMSC 360"': 'UBMSC_360',
}


TIPOS_MOTOR = {
    'CI V6 4.3 L': 'V6_43',
    'CI V6 4.4 L': 'V6_44',
    'CI V6 4.5 L': 'V6_45',
    'CI V6 4.8 L': 'V6_48',
    'CI V8 5.7 L': 'V8_57',
}


MARCAS_BOMBA = {
    'DANFOS': 'DANFOSS',
    'DANFOSS': 'DANFOSS',
    'KAWASAKI': 'KAWASAKI',
    'KPM': 'KPM',
}


MARCAS_MANIFOLD = {
    'VORDCAB': 'VORDCAB',
    'OTRO': 'OTRO',
}


def texto_comparable(valor):
    """Devuelve texto normalizado para comparaciones, sin alterar el original."""
    if valor is None:
        return ''

    texto = ' '.join(str(valor).strip().split())
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )
    return texto.upper()


def normalizar_texto(valor, marcadores_extra=None):
    """
    Convierte marcadores completos como N/A, NV, NT o SIN BOMBA a None.

    No elimina valores parcialmente útiles como N/A-216 o NV/ VDC21420012.
    """
    if valor is None:
        return None

    original = ' '.join(str(valor).strip().split())
    comparable = texto_comparable(original)

    marcadores = set(VALORES_SIN_DATO)
    if marcadores_extra:
        marcadores.update(texto_comparable(item) for item in marcadores_extra)

    if comparable in marcadores:
        return None

    return original or None


def normalizar_eco(valor):
    """Hace equivalentes 121, U121, U-121 y U-0121."""
    if valor is None:
        return None

    limpio = re.sub(r'[^A-Z0-9]', '', str(valor).strip().upper())
    if limpio.startswith('U'):
        limpio = limpio[1:]

    if limpio.isdigit():
        return str(int(limpio))

    return limpio or None


def valor_choice(modelo, campo, candidatos):
    """Selecciona el primer candidato compatible con los choices del modelo."""
    choices = {
        str(valor)
        for valor, _etiqueta in modelo._meta.get_field(campo).choices
    }

    for candidato in candidatos:
        if candidato is not None and str(candidato) in choices:
            return str(candidato)

    return None


def actualizar_campos(instancia, valores, sobrescribir=False, using='default'):
    """Completa campos vacíos o sobrescribe cuando se solicita explícitamente."""
    modificados = []

    for campo, nuevo_valor in valores.items():
        valor_actual = getattr(instancia, campo)

        if nuevo_valor is None:
            continue

        if sobrescribir or valor_actual in (None, ''):
            if valor_actual != nuevo_valor:
                setattr(instancia, campo, nuevo_valor)
                modificados.append(campo)

    if modificados:
        instancia.save(using=using, update_fields=modificados)

    return bool(modificados)


class Command(BaseCommand):
    help = (
        'Importa motores, bombas, manifolds y datos técnicos de UBM desde '
        'la base legacy configurada en DATABASES.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--legacy-alias',
            default='legacy_activos',
            help='Alias de DATABASES para la base legacy.',
        )
        parser.add_argument(
            '--destino-alias',
            default='default',
            help='Alias de DATABASES para SAVIA.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta toda la importación y revierte la transacción al final.',
        )
        parser.add_argument(
            '--sobrescribir',
            action='store_true',
            help='Sobrescribe valores existentes. Sin esta opción solo llena vacíos.',
        )

    def handle(self, *args, **options):
        self.legacy_alias = options['legacy_alias']
        self.destino_alias = options['destino_alias']
        self.dry_run = options['dry_run']
        self.sobrescribir = options['sobrescribir']

        if self.legacy_alias not in connections:
            raise CommandError(
                f'No existe el alias de base de datos "{self.legacy_alias}".'
            )

        if self.destino_alias not in connections:
            raise CommandError(
                f'No existe el alias de base de datos "{self.destino_alias}".'
            )

        self.contadores = defaultdict(int)
        self.advertencias = []

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                'Importación de componentes y extensiones UBM'
            )
        )
        self.stdout.write(f'Legacy: {self.legacy_alias}')
        self.stdout.write(f'Destino: {self.destino_alias}')
        self.stdout.write(f'Dry-run: {"sí" if self.dry_run else "no"}')
        self.stdout.write(
            f'Sobrescribir: {"sí" if self.sobrescribir else "no"}'
        )

        try:
            motores_legacy = self.leer_tabla(
                '''
                SELECT mot_id, mot_tipo, mot_serie, mot_factura
                FROM motor
                ORDER BY mot_id
                '''
            )
            bombas_legacy = self.leer_tabla(
                '''
                SELECT bom_id, bom_serie, bom_marca, bom_nointerno
                FROM bomba
                ORDER BY bom_id
                '''
            )
            manifolds_legacy = self.leer_tabla(
                '''
                SELECT man_id, man_serie, man_marca
                FROM manifull
                ORDER BY man_id
                '''
            )
            ubms_legacy = self.leer_tabla(
                '''
                SELECT
                    ubm_eco,
                    ubm_tipo,
                    ubm_serie_acumulador,
                    ubm_serie_cilindro,
                    ubm_depaceite,
                    ubm_rack,
                    ubm_pedestal,
                    ubm_fkmotor,
                    ubm_fkbomba,
                    ubm_fkmanifull
                FROM ubm
                ORDER BY ubm_eco
                '''
            )
        except Exception as error:
            raise CommandError(
                f'No fue posible leer la base legacy: {error}'
            ) from error

        self.stdout.write(
            'Legacy leído: '
            f'{len(motores_legacy)} motores, '
            f'{len(bombas_legacy)} bombas, '
            f'{len(manifolds_legacy)} manifolds y '
            f'{len(ubms_legacy)} UBM.'
        )

        try:
            with transaction.atomic(using=self.destino_alias):
                motores = self.importar_motores(motores_legacy)
                bombas = self.importar_bombas(bombas_legacy)
                manifolds = self.importar_manifolds(manifolds_legacy)

                indice_activos = self.construir_indice_activos()
                self.importar_ubms(
                    ubms_legacy,
                    indice_activos,
                    motores,
                    bombas,
                    manifolds,
                )

                if self.dry_run:
                    transaction.set_rollback(True, using=self.destino_alias)
        except Exception as error:
            raise CommandError(
                f'La importación fue revertida por un error: {error}'
            ) from error

        self.imprimir_resumen()

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING(
                    'DRY-RUN finalizado: todos los cambios fueron revertidos.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Importación finalizada correctamente.')
            )

    def leer_tabla(self, consulta):
        with connections[self.legacy_alias].cursor() as cursor:
            cursor.execute(consulta)
            columnas = [columna[0] for columna in cursor.description]
            return [
                dict(zip(columnas, fila))
                for fila in cursor.fetchall()
            ]

    def importar_motores(self, filas):
        resultado = {}
        manager = Motor_UBM.objects.using(self.destino_alias)

        for fila in filas:
            legacy_id = fila['mot_id']
            serie = normalizar_texto(fila['mot_serie'])
            factura = normalizar_texto(fila['mot_factura'])
            tipo_legacy = normalizar_texto(fila['mot_tipo'])

            if serie is None:
                resultado[legacy_id] = None
                self.contadores['motores_omitidos'] += 1
                continue

            tipo_mapeado = TIPOS_MOTOR.get(texto_comparable(tipo_legacy))
            tipo = valor_choice(
                Motor_UBM,
                'tipo',
                [tipo_mapeado, tipo_legacy],
            )

            motor = manager.filter(serie__iexact=serie).first()

            if motor is None:
                motor = manager.create(
                    serie=serie,
                    factura=factura,
                    tipo=tipo,
                )
                self.contadores['motores_creados'] += 1
            else:
                actualizado = actualizar_campos(
                    motor,
                    {
                        'tipo': tipo,
                        'factura': factura,
                    },
                    sobrescribir=self.sobrescribir,
                    using=self.destino_alias,
                )
                self.contadores[
                    'motores_actualizados' if actualizado else 'motores_reutilizados'
                ] += 1

            resultado[legacy_id] = motor

        return resultado

    def importar_bombas(self, filas):
        resultado = {}
        manager = Bomba_UBM.objects.using(self.destino_alias)

        for fila in filas:
            legacy_id = fila['bom_id']
            serie = normalizar_texto(
                fila['bom_serie'],
                marcadores_extra={'SIN PLACA'},
            )
            numero_interno = normalizar_texto(fila['bom_nointerno'])
            marca_legacy = normalizar_texto(fila['bom_marca'])

            if serie is None and numero_interno is None:
                resultado[legacy_id] = None
                self.contadores['bombas_omitidas'] += 1
                continue

            if marca_legacy is None:
                marca = None
            else:
                marca_mapeada = MARCAS_BOMBA.get(
                    texto_comparable(marca_legacy)
                )
                marca = valor_choice(
                    Bomba_UBM,
                    'marca',
                    [marca_mapeada, marca_legacy, 'OTRA', 'OTRO'],
                )

            if serie is not None:
                bomba = manager.filter(serie__iexact=serie).first()
            else:
                bomba = manager.filter(
                    numero_interno__iexact=numero_interno
                ).first()

            if bomba is None:
                bomba = manager.create(
                    serie=serie,
                    marca=marca,
                    numero_interno=numero_interno,
                )
                self.contadores['bombas_creadas'] += 1
            else:
                actualizado = actualizar_campos(
                    bomba,
                    {
                        'marca': marca,
                        'numero_interno': numero_interno,
                    },
                    sobrescribir=self.sobrescribir,
                    using=self.destino_alias,
                )
                self.contadores[
                    'bombas_actualizadas' if actualizado else 'bombas_reutilizadas'
                ] += 1

            resultado[legacy_id] = bomba

        return resultado

    def importar_manifolds(self, filas):
        resultado = {}
        manager = Manifold_UBM.objects.using(self.destino_alias)

        for fila in filas:
            legacy_id = fila['man_id']
            serie = normalizar_texto(fila['man_serie'])
            marca_legacy = normalizar_texto(fila['man_marca'])

            if serie is None:
                resultado[legacy_id] = None
                self.contadores['manifolds_omitidos'] += 1
                continue

            if marca_legacy is None:
                marca = None
            else:
                marca_mapeada = MARCAS_MANIFOLD.get(
                    texto_comparable(marca_legacy)
                )
                marca = valor_choice(
                    Manifold_UBM,
                    'marca',
                    [marca_mapeada, marca_legacy, 'OTRO'],
                )

            manifold = manager.filter(serie__iexact=serie).first()

            if manifold is None:
                manifold = manager.create(
                    serie=serie,
                    marca=marca,
                )
                self.contadores['manifolds_creados'] += 1
            else:
                actualizado = actualizar_campos(
                    manifold,
                    {'marca': marca},
                    sobrescribir=self.sobrescribir,
                    using=self.destino_alias,
                )
                self.contadores[
                    'manifolds_actualizados'
                    if actualizado
                    else 'manifolds_reutilizados'
                ] += 1

            resultado[legacy_id] = manifold

        return resultado

    def construir_indice_activos(self):
        indice = defaultdict(list)

        activos = (
            Activo.objects.using(self.destino_alias)
            .filter(categoria__nombre__iexact='UBM',
                    estatus__nombre__iexact='ALTA',
            )
            .only('id', 'eco_unidad')
        )

        for activo in activos:
            clave = normalizar_eco(activo.eco_unidad)
            if clave:
                indice[clave].append(activo)

        return indice

    def importar_ubms(
        self,
        filas,
        indice_activos,
        motores,
        bombas,
        manifolds,
    ):
        manager = UBM_Activo.objects.using(self.destino_alias)

        for fila in filas:
            eco_legacy = fila['ubm_eco']
            clave_eco = normalizar_eco(eco_legacy)
            candidatos = indice_activos.get(clave_eco, [])

            if not candidatos:
                self.contadores['ubms_sin_activo'] += 1
                self.advertencias.append(
                    f'No se encontró Activo UBM para el ECO legacy {eco_legacy}.'
                )
                continue

            if len(candidatos) > 1:
                self.contadores['ubms_eco_ambiguo'] += 1
                ids = ', '.join(str(item.pk) for item in candidatos)
                self.advertencias.append(
                    f'ECO legacy {eco_legacy} coincide con varios Activo: {ids}.'
                )
                continue

            activo = candidatos[0]
            ubm, creada = manager.get_or_create(activo=activo)

            if creada:
                self.contadores['ubms_creadas'] += 1
            else:
                self.contadores['ubms_existentes'] += 1

            tipo_legacy = normalizar_texto(fila['ubm_tipo'])
            tipo_mapeado = TIPOS_UBM.get(texto_comparable(tipo_legacy))
            tipo_ubm = valor_choice(
                UBM_Activo,
                'tipo_ubm',
                [tipo_mapeado, tipo_legacy],
            )

            if tipo_legacy and tipo_ubm is None:
                self.contadores['tipos_ubm_no_mapeados'] += 1
                self.advertencias.append(
                    f'Tipo UBM no reconocido para ECO {eco_legacy}: {tipo_legacy}.'
                )

            modificados = []
            datos_basicos = {
                'tipo_ubm': tipo_ubm,
                'serie_acumulador': normalizar_texto(
                    fila['ubm_serie_acumulador']
                ),
                'serie_cilindro': normalizar_texto(
                    fila['ubm_serie_cilindro']
                ),
                'deposito_aceite': normalizar_texto(
                    fila['ubm_depaceite']
                ),
                'rack': normalizar_texto(fila['ubm_rack']),
                'pedestal': normalizar_texto(fila['ubm_pedestal']),
            }

            for campo, nuevo_valor in datos_basicos.items():
                valor_actual = getattr(ubm, campo)
                if nuevo_valor is None:
                    continue
                if self.sobrescribir or valor_actual in (None, ''):
                    if valor_actual != nuevo_valor:
                        setattr(ubm, campo, nuevo_valor)
                        modificados.append(campo)

            componentes = {
                'motor': motores.get(fila['ubm_fkmotor']),
                'bomba': bombas.get(fila['ubm_fkbomba']),
                'manifold': manifolds.get(fila['ubm_fkmanifull']),
            }

            for campo, componente in componentes.items():
                if componente is None:
                    continue

                actual_id = getattr(ubm, f'{campo}_id')
                if not self.sobrescribir and actual_id is not None:
                    continue

                filtro = {campo: componente}
                ocupada = (
                    manager.filter(**filtro)
                    .exclude(pk=ubm.pk)
                    .only('id', 'activo_id')
                    .first()
                )

                if ocupada is not None:
                    self.contadores['componentes_en_conflicto'] += 1
                    self.advertencias.append(
                        f'No se asignó {campo} al ECO {eco_legacy}: '
                        f'ya está relacionado con UBM_Activo {ocupada.pk}.'
                    )
                    continue

                if actual_id != componente.pk:
                    setattr(ubm, campo, componente)
                    modificados.append(campo)

            modificados = list(dict.fromkeys(modificados))

            if modificados:
                ubm.save(
                    using=self.destino_alias,
                    update_fields=modificados,
                )
                self.contadores['ubms_actualizadas'] += 1
            else:
                self.contadores['ubms_sin_cambios'] += 1

    def imprimir_resumen(self):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Resumen'))

        etiquetas = [
            ('Motores creados', 'motores_creados'),
            ('Motores actualizados', 'motores_actualizados'),
            ('Motores reutilizados', 'motores_reutilizados'),
            ('Motores omitidos', 'motores_omitidos'),
            ('Bombas creadas', 'bombas_creadas'),
            ('Bombas actualizadas', 'bombas_actualizadas'),
            ('Bombas reutilizadas', 'bombas_reutilizadas'),
            ('Bombas omitidas', 'bombas_omitidas'),
            ('Manifolds creados', 'manifolds_creados'),
            ('Manifolds actualizados', 'manifolds_actualizados'),
            ('Manifolds reutilizados', 'manifolds_reutilizados'),
            ('Manifolds omitidos', 'manifolds_omitidos'),
            ('Extensiones UBM creadas', 'ubms_creadas'),
            ('Extensiones UBM existentes', 'ubms_existentes'),
            ('Extensiones UBM actualizadas', 'ubms_actualizadas'),
            ('Extensiones UBM sin cambios', 'ubms_sin_cambios'),
            ('UBM sin activo SAVIA', 'ubms_sin_activo'),
            ('ECO ambiguos', 'ubms_eco_ambiguo'),
            ('Tipos UBM no mapeados', 'tipos_ubm_no_mapeados'),
            ('Componentes en conflicto', 'componentes_en_conflicto'),
        ]

        for etiqueta, clave in etiquetas:
            self.stdout.write(f'{etiqueta}: {self.contadores[clave]}')

        if self.advertencias:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Advertencias'))
            for advertencia in self.advertencias:
                self.stdout.write(f'- {advertencia}')
