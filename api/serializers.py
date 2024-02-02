from rest_framework import serializers
from dashboard.models import Inventario, Familia, Unidad, Product

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