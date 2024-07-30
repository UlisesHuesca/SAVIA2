from rest_framework import serializers
from dashboard.models import Inventario, Familia, Unidad, Product
from compras.models import Compra

class CompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compra
        fields = ['folio',]

class FamiliaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Familia
        fields = ('nombre',)

class UnidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = ('nombre',)

class ProductSerializer(serializers.ModelSerializer):
    familia = FamiliaSerializer()
    unidad = UnidadSerializer()

    class Meta:
        model = Product
        fields = ('codigo', 'nombre', 'unidad', 'familia')


class InventarioSerializer(serializers.ModelSerializer):
    producto = ProductSerializer()

    class Meta:
        model = Inventario
        fields = '__all__'