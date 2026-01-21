from django.urls import path
from .import views 

urlpatterns = [
    path('rentabilidad/costos', views.costos, name='rentabilidad-costos'),
    path('rentabilidad/add_costo/<str:tipo>', views.add_costo, name='add-costo'),
    path('rentabilidad/delete_costo/<str:tipo>/<int:pk>', views.delete_costo, name='delete-costo'),
    path('rentabilidad/reporte_costos', views.reporte_costos, name = 'reporte-costos'),
    path('rentabilidad/ingresos', views.ingresos, name='rentabilidad-ingresos'),
    path('rentabilidad/add_ingresos', views.add_ingresos, name='add-ingreso'),
    path('rentabilidad/delete_ingreso/<int:pk>', views.delete_ingreso, name='delete-ingreso'),
    path('rentabilidad/reporte_ingresos', views.reporte_ingresos, name = 'reporte-ingresos'),
    path('rentabilidad/depreciaciones', views.depreciaciones, name='rentabilidad-depreciaciones'),
    path('rentabilidad/add_depreciacion', views.add_depreciacion, name='add-depreciacion'),
    path('rentabilidad/reporte_depreciaciones', views.reporte_depreciaciones, name = 'reporte-depreciaciones'),
    path('rentabilidad/rentabilidad_resumen', views.reporte_rentabilidad_mensual, name = 'rentabilidad-resumen'),
    path('rentabilidad/conceptos_costos/<int:pk>', views.conceptos_costos, name='conceptos-costos'),
    path('rentabilidad/costos/carga-excel/', views.carga_costos_excel, name='carga-costos-excel'),
]