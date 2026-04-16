from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    nombre_display = models.CharField(max_length=100, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class CategoriaIngreso(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categorias_ingreso')
    nombre = models.CharField(max_length=100)
    icono = models.CharField(max_length=10, default='💰')

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    TIPOS = [
        ('gastos_fijos', 'Gastos Fijos'),
        ('deseos', 'Deseos'),
        ('ahorros', 'Ahorros'),
        ('custom', 'Personalizada'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categorias')
    nombre = models.CharField(max_length=100)
    icono = models.CharField(max_length=10, default='📂')
    tipo = models.CharField(max_length=20, choices=TIPOS, default='custom')
    orden = models.IntegerField(default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

    @property
    def es_ahorros(self):
        return self.tipo == 'ahorros'


class Subcategoria(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias')
    nombre = models.CharField(max_length=100)
    icono = models.CharField(max_length=10, default='•')

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.categoria.nombre} > {self.nombre}"


class PresupuestoTotal(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='presupuestos_totales')
    mes = models.IntegerField()
    anio = models.IntegerField()
    monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ['usuario', 'mes', 'anio']


class Presupuesto(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='presupuestos')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='presupuestos')
    mes = models.IntegerField()
    anio = models.IntegerField()
    monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ['usuario', 'categoria', 'mes', 'anio']


class PresupuestoSubcategoria(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='presupuestos_sub')
    subcategoria = models.ForeignKey(Subcategoria, on_delete=models.CASCADE, related_name='presupuestos')
    mes = models.IntegerField()
    anio = models.IntegerField()
    monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ['usuario', 'subcategoria', 'mes', 'anio']


class Gasto(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gastos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='gastos')
    subcategoria = models.ForeignKey(Subcategoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='gastos')
    fecha = models.DateField(default=timezone.now)
    detalle = models.CharField(max_length=300, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado_en']


class Ingreso(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ingresos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    categoria = models.ForeignKey(CategoriaIngreso, on_delete=models.SET_NULL, null=True, related_name='ingresos')
    fecha = models.DateField(default=timezone.now)
    detalle = models.CharField(max_length=300, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado_en']


class Ahorro(models.Model):
    TIPOS = [
        ('deposito', 'Depósito'),
        ('retiro', 'Retiro'),
        ('gasto', 'Gasto desde ahorros'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ahorros')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField(default=timezone.now)
    detalle = models.CharField(max_length=300, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado_en']
