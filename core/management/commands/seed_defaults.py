from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Categoria, CategoriaIngreso, Subcategoria

CATEGORIAS_GASTO = [
    ('🏠', 'Gastos Fijos', 'gastos_fijos', 0, ['Renta / Hipoteca', 'Servicios', 'Suscripciones', 'Transporte']),
    ('✨', 'Deseos',       'deseos',       1, ['Salidas', 'Ropa', 'Entretenimiento', 'Restaurantes']),
]

CATEGORIAS_INGRESO = [
    ('Sueldo',    '💼'),
    ('Freelance', '💻'),
    ('Regalo',    '🎁'),
    ('Otro',      '📥'),
]


class Command(BaseCommand):
    help = 'Crea categorías e ingresos predeterminados para usuarios que no los tienen'

    def handle(self, *args, **options):
        for user in User.objects.all():
            creadas = 0

            for icono, nombre, tipo, orden, subcats in CATEGORIAS_GASTO:
                if not Categoria.objects.filter(usuario=user, tipo=tipo).exists():
                    cat = Categoria.objects.create(
                        usuario=user, nombre=nombre, icono=icono, tipo=tipo, orden=orden
                    )
                    for sub in subcats:
                        Subcategoria.objects.create(categoria=cat, nombre=sub, icono='•')
                    creadas += 1
                    self.stdout.write(f'  [{user.email}] Categoría "{nombre}" creada')

            for nombre, icono in CATEGORIAS_INGRESO:
                if not CategoriaIngreso.objects.filter(usuario=user, nombre=nombre).exists():
                    CategoriaIngreso.objects.create(usuario=user, nombre=nombre, icono=icono)
                    creadas += 1
                    self.stdout.write(f'  [{user.email}] Ingreso "{nombre}" creado')

            if creadas == 0:
                self.stdout.write(f'  [{user.email}] Ya tiene todo, sin cambios')

        self.stdout.write(self.style.SUCCESS('\n✓ Listo.'))