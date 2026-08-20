from django.core.validators import FileExtensionValidator
from django.db import models


class CFDI(models.Model):

    TIPO_COMPROBANTE_CHOICES = [
        ('I', 'Ingreso'),
        ('E', 'Egreso'),
        ('P', 'Pago'),
        ('N', 'Nómina'),
        ('T', 'Traslado'),
    ]

    ESTATUS_CHOICES = [
        ('PENDIENTE', 'Pendiente de vincular'),
        ('VINCULADO', 'Vinculado'),
        ('CANCELADO', 'Cancelado en SAT'),
    ]

    # Identificación fiscal
    uuid = models.CharField(max_length=36, unique=True, db_index=True, verbose_name='UUID',)
    version_cfdi = models.CharField(max_length=10, null=True, blank=True, verbose_name='Versión CFDI',)
    tipo_comprobante = models.CharField(max_length=1, choices=TIPO_COMPROBANTE_CHOICES, null=True, blank=True,verbose_name='Tipo de comprobante',)
    serie = models.CharField(max_length=30, null=True, blank=True,)
    folio = models.CharField(max_length=50, null=True, blank=True,db_index=True,)
    fecha_emision = models.DateTimeField(null=True, blank=True,)
    fecha_timbrado = models.DateTimeField(null=True,blank=True,db_index=True,)
    rfc_emisor = models.CharField(max_length=13,db_index=True,)
    nombre_emisor = models.CharField(max_length=300,null=True,blank=True,)
    regimen_fiscal_emisor = models.CharField(max_length=10,null=True,blank=True,)
    rfc_receptor = models.CharField(max_length=13,db_index=True,)
    nombre_receptor = models.CharField(max_length=300,null=True,blank=True,)
    regimen_fiscal_receptor = models.CharField(max_length=10,null=True,blank=True,)
    domicilio_fiscal_receptor = models.CharField(max_length=10,null=True,blank=True,)
    uso_cfdi = models.CharField(max_length=10,null=True,blank=True,)
    subtotal = models.DecimalField(max_digits=18,decimal_places=6,default=0,)
    impuestos_trasladados = models.DecimalField(max_digits=18,decimal_places=6,default=0,)
    impuestos_retenidos = models.DecimalField(max_digits=18,decimal_places=6,default=0,)
    total = models.DecimalField(max_digits=18,decimal_places=6,default=0,db_index=True,)
    moneda = models.CharField(max_length=10,null=True,blank=True,)
    tipo_cambio = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True,)
    forma_pago = models.CharField(max_length=10,null=True,blank=True,)
    metodo_pago = models.CharField(max_length=10,null=True,blank=True,)
    lugar_expedicion = models.CharField(max_length=10, null=True, blank=True,)
    # Archivos
    archivo_xml = models.FileField(upload_to='boveda_xml/xml/%Y/%m/',validators=[FileExtensionValidator(['xml'])],)
    # Control de SAVIA
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='PENDIENTE',db_index=True,)
    estado_sat = models.CharField(max_length=50, null=True, blank=True,)
    fecha_validacion_sat = models.DateTimeField(null=True,blank=True,)
    subido_por = models.ForeignKey('user.Profile', on_delete=models.PROTECT,related_name='cfdi_boveda_subidos',)
    fecha_subido = models.DateTimeField(auto_now_add=True,db_index=True,)

    class Meta:
        ordering = ['-fecha_timbrado', '-fecha_subido']
        verbose_name = 'CFDI'
        verbose_name_plural = 'CFDI'
        indexes = [
            models.Index(
                fields=['rfc_emisor', 'fecha_timbrado'],
                name='cfdi_emisor_fecha_idx',
            ),
            models.Index(
                fields=['rfc_receptor', 'fecha_timbrado'],
                name='cfdi_receptor_fecha_idx',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.uuid:
            self.uuid = self.uuid.strip().upper()

        if self.rfc_emisor:
            self.rfc_emisor = self.rfc_emisor.strip().upper()

        if self.rfc_receptor:
            self.rfc_receptor = self.rfc_receptor.strip().upper()

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.uuid} - {self.nombre_emisor}'
# Create your models here.
