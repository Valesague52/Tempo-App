from django.core.management.base import BaseCommand
from core.models import Categoria, CategoriaIngreso

MAPA_CATEGORIAS = {
    '<i class="fi fi-sr-home"></i>':      '🏠',
    '<i class="fi fi-rr-sparkles"></i>':  '✨',
    '<i class="fi fi-rr-piggy-bank"></i>':'🐷',
}

MAPA_INGRESOS = {
    '<i class="fi fi-sr-briefcase"></i>':       '💼',
    '<i class="fi fi-rs-computer"></i>':        '💻',
    '<i class="fi fi-rr-gift"></i>':            '🎁',
    '<i class="fi fi-br-passive-income"></i>':  '📥',
}

class Command(BaseCommand):
    help = 'Reemplaza íconos HTML rotos por emojis en la base de datos'

    def handle(self, *args, **options):
        total = 0

        for cat in Categoria.objects.all():
            nuevo = MAPA_CATEGORIAS.get(cat.icono)
            if nuevo:
                cat.icono = nuevo
                cat.save(update_fields=['icono'])
                self.stdout.write(f'  Categoria [{cat.nombre}]: → {nuevo}')
                total += 1

        for ci in CategoriaIngreso.objects.all():
            nuevo = MAPA_INGRESOS.get(ci.icono)
            if nuevo:
                ci.icono = nuevo
                ci.save(update_fields=['icono'])
                self.stdout.write(f'  CategoriaIngreso [{ci.nombre}]: → {nuevo}')
                total += 1

        self.stdout.write(self.style.SUCCESS(f'\n✓ {total} íconos corregidos.'))
