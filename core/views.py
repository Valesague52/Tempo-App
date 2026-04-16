from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum
from decimal import Decimal, InvalidOperation
import re
from datetime import date

from .models import (
    PerfilUsuario, CategoriaIngreso, Categoria, Subcategoria,
    PresupuestoTotal, Presupuesto, PresupuestoSubcategoria,
    Gasto, Ingreso, Ahorro
)

# ═══════════════════════════════════════════════════════════
#   HELPERS
# ═══════════════════════════════════════════════════════════

def crear_categorias_default(usuario):
    defaults = [
        ('🏠', 'Gastos Fijos', 'gastos_fijos', 0),
        ('✨', 'Deseos',        'deseos',       1),
    ]
    for icono, nombre, tipo, orden in defaults:
        cat = Categoria.objects.create(usuario=usuario, nombre=nombre, icono=icono, tipo=tipo, orden=orden)
        if tipo == 'gastos_fijos':
            for sub in ['Renta / Hipoteca', 'Servicios', 'Suscripciones', 'Transporte']:
                Subcategoria.objects.create(categoria=cat, nombre=sub, icono='•')
        elif tipo == 'deseos':
            for sub in ['Salidas', 'Ropa', 'Entretenimiento', 'Restaurantes']:
                Subcategoria.objects.create(categoria=cat, nombre=sub, icono='•')
    for nombre, icono in [('Sueldo', '💼'), ('Freelance', '💻'), ('Regalo', '🎁'), ('Otro', '📥')]:
        CategoriaIngreso.objects.create(usuario=usuario, nombre=nombre, icono=icono)


def safe_decimal(value, default=Decimal('0')):
    try:
        return Decimal(str(value).replace(',', '.'))
    except (InvalidOperation, TypeError, ValueError):
        return default


def get_saldo_acumulado(usuario, hasta_mes, hasta_anio):
    """
    Saldo ACUMULADO hasta el mes indicado (inclusive).
    Suma todos los ingresos y gastos desde siempre hasta ese mes/año,
    MENOS los depósitos a la alcancía (que salen del flujo normal).
    Más los retiros de la alcancía (que vuelven al flujo).
    """
    # Todos los ingresos hasta ese mes
    ingresos = Ingreso.objects.filter(
        usuario=usuario,
        fecha__lte=date(hasta_anio, hasta_mes, 31 if hasta_mes in [1,3,5,7,8,10,12] else 30 if hasta_mes != 2 else 28)
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    # Todos los gastos hasta ese mes (usando el último día del mes de forma simple)
    from django.db.models import Q
    gastos = Gasto.objects.filter(
        usuario=usuario,
        fecha__year__lt=hasta_anio
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')
    gastos += Gasto.objects.filter(
        usuario=usuario,
        fecha__year=hasta_anio,
        fecha__month__lte=hasta_mes
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    ingresos_total = Ingreso.objects.filter(
        usuario=usuario,
        fecha__year__lt=hasta_anio
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')
    ingresos_total += Ingreso.objects.filter(
        usuario=usuario,
        fecha__year=hasta_anio,
        fecha__month__lte=hasta_mes
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    # Depósitos a alcancía (se restan del saldo, salieron del flujo)
    depositos = Ahorro.objects.filter(usuario=usuario, tipo='deposito').aggregate(t=Sum('monto'))['t'] or Decimal('0')
    # Retiros (vuelven al saldo)
    retiros = Ahorro.objects.filter(usuario=usuario, tipo='retiro').aggregate(t=Sum('monto'))['t'] or Decimal('0')

    return ingresos_total - gastos - depositos + retiros


def get_resumen_mes(usuario, mes, anio):
    """Totales del mes específico + saldo acumulado hasta ese mes."""
    total_gastos = Gasto.objects.filter(
        usuario=usuario, fecha__month=mes, fecha__year=anio
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    total_ingresos = Ingreso.objects.filter(
        usuario=usuario, fecha__month=mes, fecha__year=anio
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    pt = PresupuestoTotal.objects.filter(usuario=usuario, mes=mes, anio=anio).first()
    presupuesto = pt.monto if pt else Decimal('0')

    # Saldo acumulado: todos los ingresos - todos los gastos - depósitos alcancía + retiros
    saldo_acumulado = get_saldo_acumulado(usuario, mes, anio)

    return {
        'total_gastos':    total_gastos,
        'total_ingresos':  total_ingresos,
        'presupuesto':     presupuesto,
        'saldo':           saldo_acumulado,  # saldo real disponible
        'saldo_mes':       total_ingresos - total_gastos,  # solo del mes
    }


def get_total_ahorros(usuario):
    dep  = Ahorro.objects.filter(usuario=usuario, tipo='deposito').aggregate(t=Sum('monto'))['t'] or Decimal('0')
    ret  = Ahorro.objects.filter(usuario=usuario, tipo='retiro').aggregate(t=Sum('monto'))['t']   or Decimal('0')
    gas  = Ahorro.objects.filter(usuario=usuario, tipo='gasto').aggregate(t=Sum('monto'))['t']    or Decimal('0')
    return dep - ret - gas


# ═══════════════════════════════════════════════════════════
#   AUTH
# ═══════════════════════════════════════════════════════════

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        try:
            u = User.objects.get(email=email)
            user = authenticate(request, username=u.username, password=password)
            if user:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Contraseña incorrecta.')
        except User.DoesNotExist:
            messages.error(request, 'No existe una cuenta con ese correo.')
    return render(request, 'auth/login.html')


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form_data = {}
    if request.method == 'POST':
        nombre    = request.POST.get('nombre', '').strip()
        email     = request.POST.get('email', '').strip().lower()
        password  = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        form_data = {'nombre': nombre, 'email': email}

        errores = []
        if not nombre:
            errores.append('El nombre es obligatorio.')
        if not email or '@' not in email:
            errores.append('Correo electrónico inválido.')
        elif User.objects.filter(email=email).exists():
            errores.append('Ya existe una cuenta con ese correo.')
        if len(password) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres.')
        elif not re.search(r'[A-Z]', password):
            errores.append('La contraseña necesita al menos una mayúscula.')
        elif not re.search(r'[0-9]', password):
            errores.append('La contraseña necesita al menos un número.')
        if password and password2 and password != password2:
            errores.append('Las contraseñas no coinciden.')

        if errores:
            for e in errores:
                messages.error(request, e)
            return render(request, 'auth/registro.html', {'form_data': form_data})

        base = re.sub(r'[^a-z0-9]', '', email.split('@')[0]) or 'user'
        username = base
        n = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{n}"; n += 1

        user = User.objects.create_user(username=username, email=email, password=password, first_name=nombre)
        PerfilUsuario.objects.create(usuario=user, nombre_display=nombre)
        crear_categorias_default(user)
        login(request, user)
        messages.success(request, f'¡Bienvenid@, {nombre}! Tu cuenta está lista 🎉')
        return redirect('dashboard')

    return render(request, 'auth/registro.html', {'form_data': form_data})


def logout_view(request):
    logout(request)
    return redirect('login')


# ═══════════════════════════════════════════════════════════
#   DASHBOARD
# ═══════════════════════════════════════════════════════════

MESES = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
         'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

@login_required
def dashboard(request):
    hoy  = date.today()
    mes  = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))

    resumen = get_resumen_mes(request.user, mes, anio)
    ultimos_gastos = Gasto.objects.filter(
        usuario=request.user, fecha__month=mes, fecha__year=anio
    ).select_related('categoria', 'subcategoria')[:8]

    categorias = Categoria.objects.filter(
        usuario=request.user, activa=True
    ).exclude(tipo='ahorros')

    cat_data = []
    for cat in categorias:
        gastado = Gasto.objects.filter(
            usuario=request.user, categoria=cat, fecha__month=mes, fecha__year=anio
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')
        pres = Presupuesto.objects.filter(
            usuario=request.user, categoria=cat, mes=mes, anio=anio
        ).first()
        presupuesto = pres.monto if pres else Decimal('0')
        pct = int(gastado / presupuesto * 100) if presupuesto > 0 else 0
        cat_data.append({
            'categoria':   cat,
            'gastado':     gastado,
            'presupuesto': presupuesto,
            'porcentaje':  min(pct, 100),
            'excedido':    gastado > presupuesto and presupuesto > 0,
        })

    total_ahorros = get_total_ahorros(request.user)
    mes_ant  = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1
    mes_sig  = mes + 1 if mes < 12 else 1
    anio_sig = anio if mes < 12 else anio + 1

    return render(request, 'dashboard.html', {
        'resumen': resumen, 'ultimos_gastos': ultimos_gastos,
        'cat_data': cat_data, 'total_ahorros': total_ahorros,
        'mes': mes, 'anio': anio, 'mes_nombre': MESES[mes],
        'mes_ant': mes_ant, 'anio_ant': anio_ant,
        'mes_sig': mes_sig, 'anio_sig': anio_sig,
        'es_mes_actual': mes == hoy.month and anio == hoy.year,
    })


# ═══════════════════════════════════════════════════════════
#   GASTOS
# ═══════════════════════════════════════════════════════════

@login_required
def gastos_view(request):
    hoy  = date.today()
    mes  = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))

    gastos = Gasto.objects.filter(
        usuario=request.user, fecha__month=mes, fecha__year=anio
    ).select_related('categoria', 'subcategoria')

    categorias = Categoria.objects.filter(
        usuario=request.user, activa=True
    ).exclude(tipo='ahorros')

    resumen = get_resumen_mes(request.user, mes, anio)

    mes_ant  = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1
    mes_sig  = mes + 1 if mes < 12 else 1
    anio_sig = anio if mes < 12 else anio + 1

    return render(request, 'gastos.html', {
        'gastos': gastos, 'categorias': categorias, 'resumen': resumen,
        'mes': mes, 'anio': anio, 'mes_nombre': MESES[mes],
        'mes_ant': mes_ant, 'anio_ant': anio_ant,
        'mes_sig': mes_sig, 'anio_sig': anio_sig,
        'hoy': hoy.strftime('%Y-%m-%d'),
    })


@login_required
@require_POST
def agregar_gasto(request):
    try:
        monto = safe_decimal(request.POST.get('monto'))
        if monto <= 0:
            messages.error(request, 'El monto debe ser mayor a 0.')
            return redirect(request.POST.get('next', 'gastos'))

        cat_id = request.POST.get('categoria')
        sub_id = request.POST.get('subcategoria') or None
        fecha  = date.fromisoformat(request.POST.get('fecha', date.today().isoformat()))
        detalle= request.POST.get('detalle', '').strip()

        cat = get_object_or_404(Categoria, pk=cat_id, usuario=request.user)
        if cat.es_ahorros:
            messages.error(request, 'Para mover dinero a ahorros, usa la sección Ahorros.')
            return redirect(request.POST.get('next', 'gastos'))

        sub = None
        if sub_id:
            sub = get_object_or_404(Subcategoria, pk=sub_id, categoria=cat)

        Gasto.objects.create(
            usuario=request.user, monto=monto, categoria=cat,
            subcategoria=sub, fecha=fecha, detalle=detalle
        )
        messages.success(request, f'Gasto de ${monto:,.0f} registrado ✓')
    except Exception as e:
        messages.error(request, f'Error al registrar: {str(e)}')

    return redirect(request.POST.get('next', 'gastos'))


@login_required
@require_POST
def editar_gasto(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk, usuario=request.user)
    try:
        monto = safe_decimal(request.POST.get('monto'))
        if monto <= 0:
            messages.error(request, 'El monto debe ser mayor a 0.')
            return redirect('gastos')

        cat_id = request.POST.get('categoria')
        sub_id = request.POST.get('subcategoria') or None
        cat    = get_object_or_404(Categoria, pk=cat_id, usuario=request.user)

        gasto.monto       = monto
        gasto.categoria   = cat
        gasto.subcategoria= get_object_or_404(Subcategoria, pk=sub_id, categoria=cat) if sub_id else None
        gasto.fecha       = date.fromisoformat(request.POST.get('fecha', gasto.fecha.isoformat()))
        gasto.detalle     = request.POST.get('detalle', '').strip()
        gasto.save()
        messages.success(request, 'Gasto actualizado ✓')
    except Exception as e:
        messages.error(request, f'Error al editar: {str(e)}')
    return redirect('gastos')


@login_required
def eliminar_gasto(request, pk):
    get_object_or_404(Gasto, pk=pk, usuario=request.user).delete()
    messages.success(request, 'Gasto eliminado.')
    return redirect(request.GET.get('next', 'gastos'))


# ═══════════════════════════════════════════════════════════
#   INGRESOS
# ═══════════════════════════════════════════════════════════

@login_required
def ingresos_view(request):
    hoy  = date.today()
    mes  = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))

    ingresos = Ingreso.objects.filter(
        usuario=request.user, fecha__month=mes, fecha__year=anio
    ).select_related('categoria')

    categorias_ingreso = CategoriaIngreso.objects.filter(usuario=request.user)
    resumen = get_resumen_mes(request.user, mes, anio)

    mes_ant  = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1
    mes_sig  = mes + 1 if mes < 12 else 1
    anio_sig = anio if mes < 12 else anio + 1

    return render(request, 'ingresos.html', {
        'ingresos': ingresos, 'categorias_ingreso': categorias_ingreso,
        'resumen': resumen,
        'mes': mes, 'anio': anio, 'mes_nombre': MESES[mes],
        'mes_ant': mes_ant, 'anio_ant': anio_ant,
        'mes_sig': mes_sig, 'anio_sig': anio_sig,
        'hoy': hoy.strftime('%Y-%m-%d'),
    })


@login_required
@require_POST
def agregar_ingreso(request):
    try:
        monto = safe_decimal(request.POST.get('monto'))
        if monto <= 0:
            messages.error(request, 'El monto debe ser mayor a 0.')
            return redirect('ingresos')
        cat = get_object_or_404(CategoriaIngreso, pk=request.POST['categoria'], usuario=request.user)
        fecha = date.fromisoformat(request.POST.get('fecha', date.today().isoformat()))
        Ingreso.objects.create(
            usuario=request.user, monto=monto, categoria=cat,
            fecha=fecha, detalle=request.POST.get('detalle', '').strip()
        )
        messages.success(request, f'Ingreso de ${monto:,.0f} registrado ✓')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    return redirect('ingresos')


@login_required
@require_POST
def editar_ingreso(request, pk):
    ing = get_object_or_404(Ingreso, pk=pk, usuario=request.user)
    try:
        ing.monto     = safe_decimal(request.POST.get('monto'))
        ing.categoria = get_object_or_404(CategoriaIngreso, pk=request.POST['categoria'], usuario=request.user)
        ing.fecha     = date.fromisoformat(request.POST.get('fecha', ing.fecha.isoformat()))
        ing.detalle   = request.POST.get('detalle', '').strip()
        ing.save()
        messages.success(request, 'Ingreso actualizado ✓')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    return redirect('ingresos')


@login_required
def eliminar_ingreso(request, pk):
    get_object_or_404(Ingreso, pk=pk, usuario=request.user).delete()
    messages.success(request, 'Ingreso eliminado.')
    return redirect('ingresos')


# ═══════════════════════════════════════════════════════════
#   PRESUPUESTO
# ═══════════════════════════════════════════════════════════

@login_required
def presupuesto_view(request):
    hoy  = date.today()
    mes  = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))

    categorias = Categoria.objects.filter(
        usuario=request.user, activa=True
    ).exclude(tipo='ahorros').prefetch_related('subcategorias')

    presupuesto_total = PresupuestoTotal.objects.filter(
        usuario=request.user, mes=mes, anio=anio
    ).first()

    cat_pres = []
    for cat in categorias:
        pres = Presupuesto.objects.filter(
            usuario=request.user, categoria=cat, mes=mes, anio=anio
        ).first()
        # Gastado en la categoría
        gastado_cat = Gasto.objects.filter(
            usuario=request.user, categoria=cat, fecha__month=mes, fecha__year=anio
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

        subs = []
        for sub in cat.subcategorias.all():
            sp = PresupuestoSubcategoria.objects.filter(
                usuario=request.user, subcategoria=sub, mes=mes, anio=anio
            ).first()
            gastado_sub = Gasto.objects.filter(
                usuario=request.user, subcategoria=sub, fecha__month=mes, fecha__year=anio
            ).aggregate(t=Sum('monto'))['t'] or Decimal('0')
            presupuesto_sub = sp.monto if sp else Decimal('0')
            pct_sub = int(gastado_sub / presupuesto_sub * 100) if presupuesto_sub > 0 else 0
            subs.append({
                'sub':          sub,
                'monto':        presupuesto_sub,
                'gastado':      gastado_sub,
                'porcentaje':   min(pct_sub, 100),
                'excedido':     gastado_sub > presupuesto_sub and presupuesto_sub > 0,
                'disponible':   max(presupuesto_sub - gastado_sub, Decimal('0')),
            })

        monto_pres = pres.monto if pres else Decimal('0')
        pct_cat = int(gastado_cat / monto_pres * 100) if monto_pres > 0 else 0
        cat_pres.append({
            'cat':         cat,
            'monto':       monto_pres,
            'gastado':     gastado_cat,
            'porcentaje':  min(pct_cat, 100),
            'excedido':    gastado_cat > monto_pres and monto_pres > 0,
            'disponible':  max(monto_pres - gastado_cat, Decimal('0')),
            'subcategorias': subs,
        })

    mes_ant  = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1
    mes_sig  = mes + 1 if mes < 12 else 1
    anio_sig = anio if mes < 12 else anio + 1

    return render(request, 'presupuesto.html', {
        'presupuesto_total': presupuesto_total,
        'cat_pres':   cat_pres,
        'mes': mes, 'anio': anio, 'mes_nombre': MESES[mes],
        'mes_ant': mes_ant, 'anio_ant': anio_ant,
        'mes_sig': mes_sig, 'anio_sig': anio_sig,
    })


@login_required
@require_POST
def guardar_presupuesto(request):
    mes = int(request.POST['mes'])
    anio = int(request.POST['anio'])

    # 1. Guardar presupuesto total (opcional, no afecta a subcategorías)
    total = safe_decimal(request.POST.get('total', '0'))
    PresupuestoTotal.objects.update_or_create(
        usuario=request.user, mes=mes, anio=anio,
        defaults={'monto': total}
    )

    # 2. Guardar presupuestos de categorías y almacenarlos en un diccionario
    categoria_presupuestos = {}  # {categoria_id: monto}
    for key, val in request.POST.items():
        if key.startswith('cat_'):
            try:
                cat_id = int(key[4:])
                cat = Categoria.objects.get(pk=cat_id, usuario=request.user)
                monto = safe_decimal(val)
                Presupuesto.objects.update_or_create(
                    usuario=request.user, categoria=cat, mes=mes, anio=anio,
                    defaults={'monto': monto}
                )
                categoria_presupuestos[cat_id] = monto
            except Categoria.DoesNotExist:
                pass

    # 3. Validar y guardar presupuestos de subcategorías
    errores = []
    for key, val in request.POST.items():
        if key.startswith('sub_'):
            try:
                sub_id = int(key[4:])
                sub = Subcategoria.objects.get(pk=sub_id, categoria__usuario=request.user)
                monto_sub = safe_decimal(val)
                # Obtener el presupuesto de la categoría padre (si se actualizó en esta request, usar ese; si no, el existente)
                cat_id = sub.categoria.id
                if cat_id in categoria_presupuestos:
                    presupuesto_cat = categoria_presupuestos[cat_id]
                else:
                    # Buscar presupuesto existente de la categoría para este mes/año
                    pres_cat = Presupuesto.objects.filter(
                        usuario=request.user, categoria=sub.categoria, mes=mes, anio=anio
                    ).first()
                    presupuesto_cat = pres_cat.monto if pres_cat else Decimal('0')

                # Validación: el presupuesto de la subcategoría no puede superar el de la categoría
                if monto_sub > presupuesto_cat:
                    errores.append(
                        f'El presupuesto de "{sub.nombre}" ({monto_sub:,.0f}) no puede ser mayor '
                        f'que el presupuesto de su categoría "{sub.categoria.nombre}" ({presupuesto_cat:,.0f}).'
                    )
                else:
                    PresupuestoSubcategoria.objects.update_or_create(
                        usuario=request.user, subcategoria=sub, mes=mes, anio=anio,
                        defaults={'monto': monto_sub}
                    )
            except Subcategoria.DoesNotExist:
                pass

    if errores:
        for err in errores:
            messages.error(request, err)
    else:
        messages.success(request, 'Presupuesto guardado correctamente ✓')

    return redirect(f'/presupuesto/?mes={mes}&anio={anio}')


# ═══════════════════════════════════════════════════════════
#   CATEGORÍAS
# ═══════════════════════════════════════════════════════════

@login_required
def categorias_view(request):
    categorias   = Categoria.objects.filter(usuario=request.user, activa=True).prefetch_related('subcategorias')
    cats_ingreso = CategoriaIngreso.objects.filter(usuario=request.user)
    return render(request, 'categorias.html', {'categorias': categorias, 'categorias_ingreso': cats_ingreso})


@login_required
@require_POST
def agregar_categoria(request):
    nombre = request.POST.get('nombre', '').strip()
    icono  = request.POST.get('icono', '📂').strip() or '📂'
    if nombre:
        Categoria.objects.create(usuario=request.user, nombre=nombre, icono=icono, tipo='custom', orden=99)
        messages.success(request, f'Categoría "{nombre}" creada ✓')
    else:
        messages.error(request, 'El nombre es obligatorio.')
    return redirect('categorias')


@login_required
@require_POST
def agregar_categoria_ingreso(request):
    """Vista separada para crear categorías de ingreso."""
    nombre = request.POST.get('nombre', '').strip()
    icono  = request.POST.get('icono', '💰').strip() or '💰'
    if nombre:
        CategoriaIngreso.objects.create(usuario=request.user, nombre=nombre, icono=icono)
        messages.success(request, f'Fuente de ingreso "{nombre}" creada ✓')
    else:
        messages.error(request, 'El nombre es obligatorio.')
    return redirect('categorias')


@login_required
@require_POST
def editar_categoria(request, pk):
    cat = get_object_or_404(Categoria, pk=pk, usuario=request.user)
    cat.nombre = request.POST.get('nombre', cat.nombre).strip() or cat.nombre
    cat.icono  = request.POST.get('icono', cat.icono).strip() or cat.icono
    cat.save()
    messages.success(request, 'Categoría actualizada ✓')
    return redirect('categorias')


@login_required
def eliminar_categoria(request, pk):
    cat = get_object_or_404(Categoria, pk=pk, usuario=request.user)
    if cat.tipo in ('gastos_fijos', 'deseos', 'ahorros'):
        messages.error(request, 'No se pueden eliminar las categorías predeterminadas.')
    else:
        cat.delete()
        messages.success(request, 'Categoría eliminada.')
    return redirect('categorias')


@login_required
@require_POST
def agregar_subcategoria(request):
    cat_id = request.POST.get('categoria')
    nombre = request.POST.get('nombre', '').strip()
    icono  = request.POST.get('icono', '•').strip() or '•'
    if nombre and cat_id:
        cat = get_object_or_404(Categoria, pk=cat_id, usuario=request.user)
        Subcategoria.objects.create(categoria=cat, nombre=nombre, icono=icono)
        messages.success(request, f'Subcategoría "{nombre}" creada ✓')
    else:
        messages.error(request, 'Nombre obligatorio.')
    return redirect('categorias')


@login_required
@require_POST
def editar_subcategoria(request, pk):
    sub = get_object_or_404(Subcategoria, pk=pk, categoria__usuario=request.user)
    sub.nombre = request.POST.get('nombre', sub.nombre).strip() or sub.nombre
    sub.icono  = request.POST.get('icono', sub.icono).strip() or sub.icono
    sub.save()
    messages.success(request, 'Subcategoría actualizada ✓')
    return redirect('categorias')


@login_required
def eliminar_subcategoria(request, pk):
    sub = get_object_or_404(Subcategoria, pk=pk, categoria__usuario=request.user)
    sub.delete()
    messages.success(request, 'Subcategoría eliminada.')
    return redirect('categorias')


# ═══════════════════════════════════════════════════════════
#   AHORROS
#   - Depositar: resta del saldo disponible (se registra como
#     Ahorro tipo 'deposito'; el saldo acumulado lo descuenta)
#   - Retirar: vuelve al saldo disponible (tipo 'retiro';
#     el saldo acumulado lo suma de vuelta)
#   - Gastar: sale de la alcancía, NO afecta saldo normal
# ═══════════════════════════════════════════════════════════

@login_required
def ahorros_view(request):
    hoy   = date.today()
    mes   = int(request.GET.get('mes', hoy.month))
    anio  = int(request.GET.get('anio', hoy.year))
    total = get_total_ahorros(request.user)

    # Filtrar historial por mes seleccionado
    historial = Ahorro.objects.filter(
        usuario=request.user, fecha__month=mes, fecha__year=anio
    )

    saldo_disponible = get_saldo_acumulado(request.user, hoy.month, hoy.year)

    mes_ant  = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1
    mes_sig  = mes + 1 if mes < 12 else 1
    anio_sig = anio if mes < 12 else anio + 1

    return render(request, 'ahorros.html', {
        'total_ahorros':    total,
        'historial':        historial,
        'saldo_disponible': saldo_disponible,
        'mes': mes, 'anio': anio, 'mes_nombre': MESES[mes],
        'mes_ant': mes_ant, 'anio_ant': anio_ant,
        'mes_sig': mes_sig, 'anio_sig': anio_sig,
        'hoy': hoy.strftime('%Y-%m-%d'),
    })


@login_required
@require_POST
def agregar_movimiento_ahorro(request):
    tipo    = request.POST.get('tipo')
    monto   = safe_decimal(request.POST.get('monto', '0'))
    detalle = request.POST.get('detalle', '').strip()

    if monto <= 0:
        messages.error(request, 'El monto debe ser mayor a 0.')
        return redirect('ahorros')

    try:
        fecha = date.fromisoformat(request.POST.get('fecha', date.today().isoformat()))
    except ValueError:
        fecha = date.today()

    if tipo == 'deposito':
        hoy = date.today()
        saldo_disponible = get_saldo_acumulado(request.user, hoy.month, hoy.year)
        if monto > saldo_disponible:
            messages.error(
                request,
                f'No tienes suficiente saldo. Puedes depositar hasta ${saldo_disponible:,.0f}.'
            )
            return redirect('ahorros')

    elif tipo in ('retiro', 'gasto'):
        total_alc = get_total_ahorros(request.user)
        if monto > total_alc:
            messages.error(
                request,
                f'Tu alcancía solo tiene ${total_alc:,.0f}. No puedes retirar más de eso.'
            )
            return redirect('ahorros')

    Ahorro.objects.create(usuario=request.user, tipo=tipo, monto=monto, fecha=fecha, detalle=detalle)
    etiquetas = {'deposito': 'Depósito', 'retiro': 'Retiro', 'gasto': 'Gasto'}
    messages.success(request, f'{etiquetas.get(tipo, tipo)} de ${monto:,.0f} guardado ✓')
    return redirect('ahorros')


@login_required
def eliminar_ahorro(request, pk):
    get_object_or_404(Ahorro, pk=pk, usuario=request.user).delete()
    messages.success(request, 'Movimiento eliminado.')
    return redirect('ahorros')


# ═══════════════════════════════════════════════════════════
#   INFORMES
# ═══════════════════════════════════════════════════════════

@login_required
def informes_view(request):
    anio = int(request.GET.get('anio', date.today().year))
    return render(request, 'informes.html', {
        'anio': anio, 'anio_ant': anio - 1, 'anio_sig': anio + 1,
    })


# ═══════════════════════════════════════════════════════════
#   APIs JSON
# ═══════════════════════════════════════════════════════════

@login_required
def api_subcategorias(request, categoria_id):
    subs = Subcategoria.objects.filter(categoria_id=categoria_id, categoria__usuario=request.user)
    return JsonResponse({'subcategorias': [
        {'id': s.pk, 'nombre': s.nombre, 'icono': s.icono} for s in subs
    ]})


@login_required
def api_dashboard_data(request):
    hoy  = date.today()
    mes  = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))

    categorias = Categoria.objects.filter(usuario=request.user, activa=True).exclude(tipo='ahorros')
    COLORS = {'gastos_fijos': '#FF6B8A', 'deseos': '#7997E6', 'custom': '#3CDDAA'}

    labels, gastados, presupuestos, colores = [], [], [], []
    for cat in categorias:
        g = Gasto.objects.filter(
            usuario=request.user, categoria=cat, fecha__month=mes, fecha__year=anio
        ).aggregate(t=Sum('monto'))['t'] or 0
        p = Presupuesto.objects.filter(usuario=request.user, categoria=cat, mes=mes, anio=anio).first()
        labels.append(f"{cat.icono} {cat.nombre}")
        gastados.append(float(g))
        presupuestos.append(float(p.monto) if p else 0)
        colores.append(COLORS.get(cat.tipo, '#A1A1AA'))

    return JsonResponse({'labels': labels, 'gastados': gastados,
                         'presupuestos': presupuestos, 'colores': colores})


@login_required
def api_informes_data(request):
    anio = int(request.GET.get('anio', date.today().year))
    MESES_C = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
    gastos_mes, ingresos_mes = [], []
    for m in range(1, 13):
        g = Gasto.objects.filter(usuario=request.user, fecha__month=m, fecha__year=anio).aggregate(t=Sum('monto'))['t'] or 0
        i = Ingreso.objects.filter(usuario=request.user, fecha__month=m, fecha__year=anio).aggregate(t=Sum('monto'))['t'] or 0
        gastos_mes.append(float(g))
        ingresos_mes.append(float(i))
    return JsonResponse({'labels': MESES_C, 'gastos': gastos_mes, 'ingresos': ingresos_mes})


@login_required
def api_presupuesto_data(request):
    """Datos de progreso de presupuesto por categoría/subcategoría para el mes."""
    hoy  = date.today()
    mes  = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))

    categorias = Categoria.objects.filter(usuario=request.user, activa=True).exclude(tipo='ahorros')
    result = []
    for cat in categorias:
        pres = Presupuesto.objects.filter(usuario=request.user, categoria=cat, mes=mes, anio=anio).first()
        gastado = Gasto.objects.filter(
            usuario=request.user, categoria=cat, fecha__month=mes, fecha__year=anio
        ).aggregate(t=Sum('monto'))['t'] or 0
        cat_data = {
            'nombre': cat.nombre, 'icono': cat.icono,
            'presupuesto': float(pres.monto) if pres else 0,
            'gastado': float(gastado),
            'subs': []
        }
        for sub in cat.subcategorias.all():
            sp = PresupuestoSubcategoria.objects.filter(usuario=request.user, subcategoria=sub, mes=mes, anio=anio).first()
            gs = Gasto.objects.filter(usuario=request.user, subcategoria=sub, fecha__month=mes, fecha__year=anio).aggregate(t=Sum('monto'))['t'] or 0
            cat_data['subs'].append({
                'nombre': sub.nombre, 'icono': sub.icono,
                'presupuesto': float(sp.monto) if sp else 0,
                'gastado': float(gs),
            })
        result.append(cat_data)
    return JsonResponse({'categorias': result})
