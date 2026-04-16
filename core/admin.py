from django.contrib import admin
from .models import PerfilUsuario, CategoriaIngreso, Categoria, Subcategoria
from .models import PresupuestoTotal, Presupuesto, PresupuestoSubcategoria
from .models import Gasto, Ingreso, Ahorro

admin.site.register(PerfilUsuario)
admin.site.register(CategoriaIngreso)
admin.site.register(Categoria)
admin.site.register(Subcategoria)
admin.site.register(PresupuestoTotal)
admin.site.register(Presupuesto)
admin.site.register(Gasto)
admin.site.register(Ingreso)
admin.site.register(Ahorro)

admin.site.site_header = "Tempo — Admin"
admin.site.site_title = "Tempo"
