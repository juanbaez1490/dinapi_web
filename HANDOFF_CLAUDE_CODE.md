# HANDOFF — Migración SilverStripe 4.3 → Django 5.2 (DINAPI)
> Última actualización: junio 2026  
> Entorno: Python 3.13 · Django 5.2 LTS · SQLite (dev) → MySQL/Postgres (prod)  
> Proyecto: `C:\C-desarrollo\dinapi_web`

---

## 1. ESTADO GENERAL

### ✅ Completado
| Área | Detalle |
|---|---|
| Configuración base | `python-decouple`, `dj-database-url`, `SECRET_KEY` en `.env` |
| BD destino | SQLite dev / MySQL-Postgres prod vía `DATABASE_URL` en `.env` |
| Migraciones | Todas aplicadas (`python manage.py migrate` limpio) |
| Datos importados | 512 páginas, 575 noticias, 1208 boletines, 279 biblioteca, 24 concursos, 47 tarjetas, 19 acordeones, 11 categorías biblioteca, 6 menús, y más |
| Validación de datos | `python manage.py validate_migration --skip-mysql` → 26 ✅ / 0 ⚠️ |
| Home | Levanta en `http://127.0.0.1:8000/` |
| URLs | Sin hardcodeos — todas usan `{% url %}` y `reverse()` |
| Admin | Proxy models por tipo de página en `apps/core/admin.py` |
| Template base | `templates/base.html` reparado (tenía `{% if %}` sin cerrar en línea 711) |

### 🔲 Pendiente (P2 — próximo sprint)
| Área | Descripción |
|---|---|
| `core/admin.py` — campos incorrectos | `SiteConfigAdmin` usa nombres de campo que no existen (ver §4) |
| Vistas de detalle faltantes | `noticias:revista_detalle`, `boletines:detalle`, `boletines:periodo_detalle`, `tarjetas:detalle`, `tarjetas:acordeon_detalle`, `concursos:detalle` |
| Tipos P2 | `DiaPIPage`, `ProtegeLoTuyoPage`, `GestorEnlacesPage` — sin view, deben quedar `activo=False` |
| Producción | Cambiar `DATABASE_URL` a MySQL/Postgres, `DEBUG=False`, `collectstatic` |
| Smoke test completo | Verificar todas las vistas con el servidor corriendo |

---

## 2. ESTRUCTURA DEL PROYECTO

```
dinapi_web/
├── apps/
│   ├── core/           # Pagina, SiteConfig, Anuncio, CarouselItem, EnlaceInteres, TemaEje
│   ├── noticias/       # Noticia, CategoriaNoticia, RevistaPage
│   ├── biblioteca/     # Biblioteca, DocumentoBiblioteca, Categoria, Etiqueta, M2M
│   ├── boletines/      # Boletin, PeriodoBoletin
│   ├── calendario/     # Actividad (AJAX endpoint en actividades_json)
│   ├── concursos/      # Concurso
│   ├── contacto/       # MensajeContacto, formulario
│   ├── menus/          # MenuDerecho, Popup (context processor global)
│   ├── reclamos/       # Reclamo (formulario con validación PDF)
│   └── tarjetas/       # TarjetaPage, Tarjeta, AcordeonPage, AcordeonItem
├── config/
│   ├── settings.py
│   └── urls.py
├── templates/
│   ├── base.html       # ← reparado junio 2026
│   └── core/home.html
├── static/
├── media/
├── db.sqlite3
├── .env                # SECRET_KEY, DATABASE_URL, DEBUG, etc.
└── manage.py
```

---

## 3. URLS REGISTRADAS

```python
# config/urls.py
/admin/           → Django admin
/noticias/        → apps.noticias.urls  (app_name='noticias')
/contacto/        → apps.contacto.urls  (app_name='contacto')
/reclamos/        → apps.reclamos.urls  (app_name='reclamos')
/calendario/      → apps.calendario.urls (app_name='calendario')
/biblioteca/      → apps.biblioteca.urls (app_name='biblioteca')
/concursos/       → apps.concursos.urls  (app_name='concursos')
/boletines/       → apps.boletines.urls  (app_name='boletines')
/tarjetas/        → apps.tarjetas.urls   (app_name='tarjetas')
/menus/           → apps.menus.urls      (app_name='menus')
/                 → apps.core.urls       (app_name='core')

# URLs por app (nombres usados en reverse() y {% url %})
core:home                → /
core:pagina_detalle      → /<slug>/
noticias:lista           → /noticias/
noticias:detalle         → /noticias/<slug>/
noticias:buscar          → /noticias/buscar/
reclamos:formulario      → /reclamos/
biblioteca:lista         → /biblioteca/
biblioteca:detalle       → /biblioteca/<slug>/
boletines:general        → /boletines/
boletines:marcas         → /boletines/marcas/
calendario:index         → /calendario/
calendario:actividades_json → /calendario/actividades/
concursos:lista          → /concursos/
concursos:detalle        → /concursos/<slug>/
tarjetas:lista           → /tarjetas/
tarjetas:acordeon        → /tarjetas/acordeon/
contacto:contact         → /contacto/   ← verificar nombre exacto
```

---

## 4. PROBLEMA CONOCIDO — `core/admin.py`

El `SiteConfigAdmin` en `apps/core/admin.py` **usa nombres de campo que no existen** en el modelo. Hay que corregirlo antes de usar el admin de SiteConfig.

### Campos reales del modelo `SiteConfig` (`apps/core/models.py`):
```python
titulo_sitio, email_contacto, email_soporte, telefono, direccion,
logo, descripcion, url_horarios, url_consultas,
url_facebook, url_instagram, url_youtube, url_twitter
```

### Corrección necesaria en `apps/core/admin.py`:
```python
# REEMPLAZAR el bloque SiteConfigAdmin actual por:
@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Identidad",        {"fields": ["titulo_sitio", "logo", "descripcion"]}),
        ("Contacto",         {"fields": ["email_contacto", "email_soporte", "telefono", "direccion"]}),
        ("URLs del footer",  {"fields": ["url_horarios", "url_consultas"]}),
        ("Redes sociales",   {"fields": ["url_facebook", "url_instagram", "url_youtube", "url_twitter"]}),
    ]
    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()
```

### Campos reales de `Anuncio`:
```python
titulo, descripcion, imagen, url, fecha_inicio, fecha_fin, activo, orden, legacy_id
```
Corrección en `AnuncioAdmin` — cambiar `url_destino` → `url`, `contenido` → `descripcion`:
```python
fields = ["titulo", "descripcion", "imagen", "url", "activo", "fecha_inicio", "fecha_fin", "orden"]
```

### Campos reales de `CarouselItem`:
```python
titulo, subtitulo, imagen, url, texto_boton, activo, orden, legacy_id
```
Corrección en `CarouselItemAdmin` — cambiar `url_destino` → `url`:
```python
fields = ["titulo", "subtitulo", "imagen", "url", "texto_boton", "activo", "orden"]
```

### Campos reales de `EnlaceInteres`:
```python
titulo, descripcion, url, icono, activo, orden, legacy_id
```
✅ `EnlaceInteresAdmin` — `fields` ya correctos.

### Campos reales de `TemaEje`:
```python
nombre, eje, pagina (FK), url_externa, legacy_id, orden, activo
```
Corrección en `TemaEjeAdmin` — quitar `descripcion`, `color`, `icono` (no existen):
```python
fields = ["nombre", "eje", "pagina", "url_externa", "activo", "orden"]
```

---

## 5. `_resolve_pagina_url` — VERSIÓN EN USO

La función activa está en **`apps/core/views.py`** (no en `utils.py`).  
El archivo `apps/core/utils.py` fue generado como referencia pero **no se importa en ningún lado** — puede borrarse o ignorarse.

### Mapeo actual (`views.py`):
```python
HomePage            → /
ContactPage         → contacto:contact
ReclamosPage        → reclamos:formulario
NoticiaPage         → noticias:lista       # ← apunta a lista, no a detalle individual
CodepiNoticiaPage   → noticias:lista
RevistaPage         → noticias:lista
BibliotecaPage      → biblioteca:lista
ConcursosPage       → concursos:lista
ConcursoJuventudPage→ concursos:lista
BoletinPage         → boletines:general
PeriodoBoletinPage  → boletines:general
BoletinMarcaPage    → boletines:marcas
PeriodoBoletinMarcaPage         → boletines:marcas
PeriodoBoletinMarcaGenericoPage → boletines:marcas
ArchivoPage         → biblioteca:lista    # ← redirige a biblioteca como fallback
ArchivoDesplegablePage → biblioteca:lista
CalendarioPage      → calendario:index
TarjetaPage         → tarjetas:lista
TarjetaSimplePage   → core:pagina_detalle/<slug>
AcordeonPage        → tarjetas:acordeon
GeneralPage / InstitucionalPage / Page / resto → core:pagina_detalle/<slug>
```

### Tipos P2 (sin view — quedar con `activo=False` en BD):
| Tipo | Acción |
|---|---|
| `DiaPIPage` | Desactivar |
| `ProtegeLoTuyoPage` | Desactivar |
| `GestorEnlacesPage` | Desactivar |

Para desactivarlos:
```bash
python manage.py shell -c "
from apps.core.models import Pagina
p2 = ['DiaPIPage', 'ProtegeLoTuyoPage', 'GestorEnlacesPage']
n = Pagina.objects.filter(tipo__in=p2).update(activo=False)
print('Desactivadas:', n)
"
```

---

## 6. COMANDO DE VALIDACIÓN

```bash
# Solo destino SQLite (sin MySQL origen):
python manage.py validate_migration --skip-mysql

# Con MySQL origen configurado en settings.DATABASES['mysql_source']:
python manage.py validate_migration --mysql-alias=mysql_source

# Resultado esperado: 26 ✅ / 0 ⚠️
```

Tablas validadas (26):
`noticias_noticia`, `noticias_categorianoticia`, `core_pagina`, `boletines_boletin`,
`boletines_periodoboletin`, `biblioteca_biblioteca`, `biblioteca_documentobiblioteca`,
`biblioteca_categoriabiblioteca`, `biblioteca_etiquetabiblioteca`, `biblioteca_imagenbiblioteca`,
`biblioteca_videobiblioteca`, `biblioteca_biblioteca_documentos`, `biblioteca_biblioteca_etiquetas`,
`concursos_concurso`, `tarjetas_tarjeta`, `tarjetas_acordeonpage`, `tarjetas_acordeonitem`,
`calendario_actividad`, `core_anuncio`, `core_carouselitem`, `core_enlaceinteres`,
`core_temaeje`, `core_siteconfig`, `reclamos_reclamo`, `menus_menuderecho`, `menus_popup`

---

## 7. CHECKLIST PARA CONTINUAR EN CLAUDE CODE

### Inmediato (bugs activos):
- [ ] Corregir `SiteConfigAdmin`, `AnuncioAdmin`, `CarouselItemAdmin`, `TemaEjeAdmin` en `apps/core/admin.py` (ver §4)
- [ ] Verificar que `/admin/` carga sin errores después de la corrección
- [ ] Desactivar páginas P2 (`DiaPIPage`, `ProtegeLoTuyoPage`, `GestorEnlacesPage`)

### Vistas faltantes (P2):
- [ ] `noticias:revista_detalle` — actualmente no existe, `RevistaPage` redirige a `noticias:lista`
- [ ] `boletines:detalle` — `BoletinPage` y `BoletinMarcaPage` sin vista de detalle individual
- [ ] `boletines:periodo_detalle` — `PeriodoBoletinPage` y variantes sin detalle
- [ ] `tarjetas:detalle` — `TarjetaPage` y `TarjetaSimplePage` sin detalle
- [ ] `tarjetas:acordeon_detalle` — `AcordeonPage` sin detalle individual (solo lista)
- [ ] `concursos:detalle` — existe la URL pero verificar que la vista funciona

### Producción:
- [ ] Cambiar `DATABASE_URL` en `.env` a MySQL o PostgreSQL
- [ ] `DEBUG=False` + `ALLOWED_HOSTS` configurado
- [ ] `python manage.py collectstatic`
- [ ] Instalar driver de BD: `pip install mysqlclient` o `pip install psycopg2-binary`
- [ ] Configurar servidor web (Nginx + Gunicorn recomendado)

### Smoke test:
```bash
# Verificar que estas URLs devuelven 200:
curl http://127.0.0.1:8000/               # home
curl http://127.0.0.1:8000/noticias/      # lista noticias
curl http://127.0.0.1:8000/biblioteca/    # biblioteca
curl http://127.0.0.1:8000/boletines/     # boletines
curl http://127.0.0.1:8000/concursos/     # concursos
curl http://127.0.0.1:8000/reclamos/      # formulario reclamos
curl http://127.0.0.1:8000/calendario/    # calendario
curl http://127.0.0.1:8000/admin/         # admin Django
```

---

## 8. PROMPT PARA CONTINUAR EN CLAUDE CODE

Copiar y pegar esto al inicio de la sesión en Claude Code:

```
Contexto: proyecto Django 5.2 en C:\C-desarrollo\dinapi_web
Migración SilverStripe 4.3 → Django completada. El sitio levanta en desarrollo.

ESTADO:
- python manage.py validate_migration --skip-mysql → 26 ✅ / 0 ⚠️
- python manage.py migrate → limpio
- Home en http://127.0.0.1:8000/ funciona
- Admin en http://127.0.0.1:8000/admin/ funciona (proxy models por tipo de página)

PROBLEMA INMEDIATO A RESOLVER:
apps/core/admin.py tiene nombres de campo incorrectos en SiteConfigAdmin,
AnuncioAdmin, CarouselItemAdmin y TemaEjeAdmin. Ver HANDOFF_CLAUDE_CODE.md §4
para los campos correctos. Corregirlos y verificar que python manage.py check
no arroja errores.

SIGUIENTE PRIORIDAD (después de corregir el admin):
1. Desactivar páginas P2: DiaPIPage, ProtegeLoTuyoPage, GestorEnlacesPage
2. Implementar vistas de detalle faltantes (ver HANDOFF_CLAUDE_CODE.md §7)
3. Preparar para producción: DATABASE_URL → MySQL, DEBUG=False, collectstatic

ARCHIVOS CLAVE:
- apps/core/admin.py     → admin con proxy models (tiene bugs en §4)
- apps/core/views.py     → home_view, pagina_detalle_view, _resolve_pagina_url
- apps/core/models.py    → Pagina (TipoPagina choices), SiteConfig, Anuncio, etc.
- apps/core/management/commands/validate_migration.py → validación de datos
- config/settings.py     → configuración con decouple + dj_database_url
- templates/base.html    → template base (reparado — tenía {% if %} sin cerrar)
- HANDOFF_CLAUDE_CODE.md → este archivo, estado completo del proyecto

Empezá leyendo apps/core/admin.py y aplicando las correcciones de §4.
```
