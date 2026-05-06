from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),

    path('gastos/', views.gastos_view, name='gastos'),
    path('gastos/agregar/', views.agregar_gasto, name='agregar_gasto'),
    path('gastos/editar/<int:pk>/', views.editar_gasto, name='editar_gasto'),
    path('gastos/eliminar/<int:pk>/', views.eliminar_gasto, name='eliminar_gasto'),

    path('ingresos/', views.ingresos_view, name='ingresos'),
    path('ingresos/agregar/', views.agregar_ingreso, name='agregar_ingreso'),
    path('ingresos/editar/<int:pk>/', views.editar_ingreso, name='editar_ingreso'),
    path('ingresos/eliminar/<int:pk>/', views.eliminar_ingreso, name='eliminar_ingreso'),

    path('presupuesto/', views.presupuesto_view, name='presupuesto'),
    path('presupuesto/guardar/', views.guardar_presupuesto, name='guardar_presupuesto'),

    path('categorias/', views.categorias_view, name='categorias'),
    path('categorias/agregar/', views.agregar_categoria, name='agregar_categoria'),
    path('categorias/agregar-ingreso/', views.agregar_categoria_ingreso, name='agregar_categoria_ingreso'),
    path('categorias/editar/<int:pk>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/eliminar/<int:pk>/', views.eliminar_categoria, name='eliminar_categoria'),
    path('subcategorias/agregar/', views.agregar_subcategoria, name='agregar_subcategoria'),
    path('subcategorias/editar/<int:pk>/', views.editar_subcategoria, name='editar_subcategoria'),
    path('subcategorias/eliminar/<int:pk>/', views.eliminar_subcategoria, name='eliminar_subcategoria'),

    path('ahorros/', views.ahorros_view, name='ahorros'),
    path('ahorros/movimiento/', views.agregar_movimiento_ahorro, name='agregar_movimiento_ahorro'),
    path('ahorros/eliminar/<int:pk>/', views.eliminar_ahorro, name='eliminar_ahorro'),

    path('informes/', views.informes_view, name='informes'),

    path('api/subcategorias/<int:categoria_id>/', views.api_subcategorias, name='api_subcategorias'),
    path('api/dashboard-data/', views.api_dashboard_data, name='api_dashboard_data'),
    path('api/informes-data/', views.api_informes_data, name='api_informes_data'),
    path('api/presupuesto-data/', views.api_presupuesto_data, name='api_presupuesto_data'),
    path('categorias/eliminar-ingreso/<int:pk>/', views.eliminar_categoria_ingreso, name='eliminar_categoria_ingreso'),
]

