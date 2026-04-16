# 🎵 Tempo* — App de Finanzas Personales

> Tus finanzas, tu ritmo. Simple, visual y sin estrés.

## Stack técnico
- **Backend:** Django 4.2
- **Base de datos:** SQLite (dev) / PostgreSQL (prod)
- **Frontend:** HTML + CSS propio (design system completo)
- **Gráficas:** Chart.js (CDN)
- **Sin dependencias JS** complejas — todo nativo

---

## 🚀 Instalación rápida

```bash
# 1. Clonar / descomprimir el proyecto
cd tempo

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Migrar base de datos
python manage.py migrate

# 5. (Opcional) Crear superusuario para el admin
python manage.py createsuperuser

# 6. Correr el servidor
python manage.py runserver
```

Abre http://127.0.0.1:8000 — ¡listo! 🎉

---

## 📁 Estructura del proyecto

```
tempo/
├── core/                      # App principal
│   ├── models.py              # Todos los modelos de datos
│   ├── views.py               # Lógica de negocio + APIs JSON
│   ├── urls.py                # Rutas
│   └── admin.py               # Panel de administración
├── templates/                 # Plantillas HTML
│   ├── base.html              # Layout con sidebar
│   ├── dashboard.html         # Inicio con gráfica donut
│   ├── gastos.html            # CRUD de gastos
│   ├── ingresos.html          # CRUD de ingresos
│   ├── presupuesto.html       # Configuración de presupuesto
│   ├── categorias.html        # Gestión de categorías
│   ├── ahorros.html           # Alcancía virtual
│   ├── informes.html          # Gráficas anuales
│   └── auth/                  # Login y registro
├── static/css/tempo.css       # Design system completo
├── tempo/settings.py          # Configuración Django
└── manage.py
```

---

## ✨ Funcionalidades

| Sección | Funciones |
|---|---|
| 🏠 Dashboard | Resumen mes, gráfica donut, navegación por meses |
| 💸 Gastos | CRUD completo, filtro por mes, categorías dinámicas |
| 💵 Ingresos | CRUD completo con categorías personalizables |
| 🎯 Presupuesto | Total + por categoría + por subcategoría |
| 🏷️ Categorías | Crear/editar/eliminar cats y subcats con íconos emoji |
| 🏦 Ahorros | Alcancía virtual: depositar, retirar, gastar |
| 📊 Informes | Gráfica anual ingresos vs gastos + tabla mensual |
| 🔐 Auth | Registro, login, logout con validaciones |

---

## 🎨 Diseño

- Paleta morada/violeta moderna sobre fondo lavanda suave
- Tipografía: **Syne** (display) + **DM Sans** (cuerpo)
- Componentes: cards, modales, toasts, progress bars
- 100% responsive (mobile-first)
- Animaciones CSS suaves

---

## 🔧 Para producción

1. Cambiar `SECRET_KEY` en `settings.py`
2. Cambiar a PostgreSQL
3. `DEBUG = False`
4. Configurar `ALLOWED_HOSTS`
5. Servir archivos estáticos con Nginx/WhiteNoise

