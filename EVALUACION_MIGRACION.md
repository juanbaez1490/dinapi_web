# Evaluación de la migración Django de DINAPI

> Evaluación realizada el 2026-05-05 contrastando `C:\C-desarrollo\dinapi_web` (proyecto Django en curso) contra el inventario del proyecto SilverStripe original (`dinapi_web_old`).

---

## Resumen ejecutivo

La migración **está bien encaminada** pero **incompleta**. Cubre aproximadamente el 60-70% del sitio público (home, noticias, biblioteca, boletines, concursos, tarjetas, acordeón, contacto, menú jerárquico). Quedan agujeros importantes en formularios de reclamos, calendario/actividades, M2M de biblioteca, anuncios/carousel/enlaces y modelo de SiteConfig efectivo. Las decisiones arquitectónicas tomadas hasta ahora son correctas y los datos legacy ya están migrados (575 noticias, 512 páginas, 1208 boletines, 279 biblioteca, 47 tarjetas, 24 concursos, 22 acordeón). **Continuar es más barato que empezar de cero.**

---

## 1. MODELOS DJANGO

### 1.1 Cobertura

**8 apps creadas**: `core`, `noticias`, `contacto`, `biblioteca`, `concursos`, `boletines`, `tarjetas`, `menus`.

| Origen SilverStripe | Destino Django | Estado |
|---|---|---|
| `Page` (base SiteTree) | `core.Pagina` con TipoPagina enum + `legacy_id`/`parent_legacy_id` | ✅ Razonable |
| `CustomSiteConfig` (DataExtension sobre SiteConfig) | `core.SiteConfig` (modelo plano) | ⚠️ Existe pero los templates no lo consumen — el footer está hardcoded |
| `Noticia`, `CategoriaNoticia` | `noticias.Noticia`, `noticias.CategoriaNoticia` | ✅ |
| `RevistaPage` | `noticias.RevistaPage` | ⚠️ Existe modelo, sin views/templates dedicados |
| `MensajeContacto` | `contacto.MensajeContacto` | ✅ Pero choices=3 (Consulta/Reclamo/Sugerencia) en lugar de los 10 reales del form de Reclamos |
| `MensajeReclamos`, `ReclamosPage`, `RandomNameUploadField` | — | ❌ **No existe app `reclamos`** — README lo declara pendiente |
| `Biblioteca`, `CategoriaBiblioteca` | `biblioteca.Biblioteca`, `biblioteca.CategoriaBiblioteca` | ⚠️ Falta lo más importante: `EtiquetaBiblioteca` y los **4 ManyToManyField** (Videos, Imagenes, Documentos, Etiquetas) |
| `Concurso` | `concursos.Concurso` con `legacy_id` y `pagina_legacy_id` | ✅ aunque sin FK real a Pagina |
| `ConcursosPage` (contenedor) | — | ❌ no existe, sólo el ítem |
| `BoletinGeneral`, `BoletinLogotiposMarcas`, `BoletinMovimientosAdministrativos`, `BoletinMarcasDocumentos` | `boletines.Boletin` con discriminador `tipo` | ✅ **Decisión arquitectónica correcta** (es lo que recomendé en el inventario) |
| `BoletinColumnaUno/Dos/Tres/Cuatro` + `PeriodoBoletinMarcaGenericoPage` | — | ❌ no representado |
| `PeriodoBoletinPage`, `PeriodoBoletinMarcaPage` | `boletines.PeriodoBoletin` con `tipo=general/marca` | ✅ |
| `Tarjeta`, `TarjetaPage`, `Acordeon`, `AcordeonPage` | `tarjetas.Tarjeta`, `TarjetaPage`, `AcordeonItem`, `AcordeonPage` | ✅ |
| `TarjetaSimple`, `TarjetaSimplePage` | — | ❌ no existe |
| `MenuDerecho`, `Popup` | `menus.MenuDerecho`, `menus.Popup` | ✅ |
| `Anuncio` | — | ❌ no existe |
| `Carousel` | — | ❌ declarado pendiente |
| `EnlaceInteres` | — | ❌ no existe |
| `Calendario`, `Actividad` | — | ❌ declarado pendiente |
| `Documento` | — | ❌ no existe |
| `Archivo`, `ArchivoPage`, `ArchivoDesplegablePage` | — | ❌ no existe |
| `Institucional` (DataObject) | — | ❌ tipo de página existe (`InstitucionalPage`) pero no el `DataObject` con `LinkInterno/LinkExterno` |
| `TemaEje` | — | ❌ no existe; `home_view` tiene la lista hardcoded |

**Veredicto modelos**: están portados los modelos centrales (≈55% por cantidad, pero ≈70% por uso real), las decisiones de unificación (Boletin discriminado, Pagina con TipoPagina enum) son correctas y los `legacy_id` permiten reimportar. Falta el ~30% de modelos secundarios pero usados (calendario, anuncios, carousel, reclamos, M2M biblioteca, tarjetas simples, archivos, documentos, enlaces).

### 1.2 Calidad de relaciones y tipos

✅ Bien resueltos:
- `ForeignKey(..., on_delete=PROTECT)` en `Noticia.categoria` — coherente con la lógica del CMS original (no podés borrar una categoría con noticias).
- `ForeignKey(..., on_delete=SET_NULL, null=True)` en `Biblioteca.categoria`, `Boletin.periodo`, `Tarjeta.pagina`, `AcordeonItem.pagina` — sano.
- `ImageField`/`FileField` con `upload_to` reflejando los folderName originales (`noticias/imagenes-noticias/`, `boletines/pdf/`, etc.).
- `SlugField` con `max_length=255` y `unique=True` para URL canónicas.
- `models.Index` en Noticia y MensajeContacto.
- `unique_together = [('legacy_id', 'tipo')]` en `Boletin` — buena decisión para distinguir registros del mismo legacy_id entre tipos.
- `TextChoices` en `Pagina.TipoPagina` y `PeriodoBoletin.Tipo`.

⚠️ Problemas reales:
- **`Biblioteca` perdió las 4 ManyToManyField**. En el original, `Biblioteca` se relaciona con `File` (Videos), `Image` (Imagenes), `File` (Documentos) y `EtiquetaBiblioteca`. En Django no hay nada de eso — la lista de detalle de la biblioteca no podrá mostrar adjuntos. Esto es el **agujero más grave** de los modelos.
- **`Pagina.parent_legacy_id` es `PositiveIntegerField` plano, no `ForeignKey('self')`**. No hay integridad referencial. El context_processor reconstruye la jerarquía en Python a partir de un dict — funciona pero es frágil ante datos inconsistentes.
- **`Concurso` no tiene `pagina = ForeignKey(Pagina)`**, sólo `pagina_legacy_id`. Mismo problema que arriba.
- **`Noticia.contenido` es `TextField`**, no rich-text. Funcionalmente OK con `|safe`, pero sin editor WYSIWYG en admin (faltaría `django-ckeditor` o `tinymce`).
- **`MensajeContacto.TEMAS_CHOICES` tiene sólo 3 opciones** (Consulta/Reclamo/Sugerencia), pero `ReclamosPage::Formulario` original tiene 10 temas distintos para reclamos formales (RedPI, IPAS, SFE Presenciales/Digitales, Agentes, etc.). Si se quiere reemplazar el `MensajeReclamos` con este modelo, faltan choices.
- **`SiteConfig` existe como modelo pero los templates no lo consumen** (`base.html` tiene email, dirección, teléfono, redes sociales hardcoded). Es código muerto hoy.

❌ Modelos faltantes con impacto: `Calendario/Actividad`, `MensajeReclamos`, `Anuncio`, `Carousel`, `EnlaceInteres`, `EtiquetaBiblioteca` + M2M, `TemaEje`, `Documento`, `Archivo`, `TarjetaSimple`.

---

## 2. TEMPLATES

### 2.1 Cobertura

**19 archivos `.html`** detectados, contra **47 `.ss`** del original (24 layouts + 12 includes + 5 emails + 6 detalles).

| `.ss` original | `.html` Django | Estado |
|---|---|---|
| `Page.ss` (wrapper raíz) | `base.html` | ✅ Bien hecho — tiene navbar dinámico, footer, popup modal, masthead |
| `Layout/HomePage.ss` | `core/home.html` | ✅ |
| `Layout/GeneralPage.ss` | `core/pagina_detalle.html` | ✅ vista por slug |
| `Layout/InstitucionalPage.ss` | `core/institucional.html` | ✅ con cards "armadas a mano" |
| `Layout/NoticiaPage.ss` + `NoticiaDetalle.ss` | `noticias/lista.html`, `detalle.html`, `busqueda.html`, `destacadas.html` | ✅ |
| `Layout/ContactPage.ss` | `contacto/formulario.html` + `email_mensaje.html` | ✅ |
| `Layout/ReclamosPage.ss` | — | ❌ no existe |
| `Layout/BibliotecaPage.ss` + `BibliotecaDetalle.ss` | `biblioteca/lista.html`, `detalle.html` | ⚠️ template existe pero la búsqueda en view sólo busca por título (no por descripción/categoría/etiqueta) |
| `Layout/ConcursosPage.ss` + `ConcursoDetalle.ss` | `concursos/lista.html`, `detalle.html` | ✅ |
| `Layout/BoletinPage.ss` + `BoletinMarcaPage.ss` | `boletines/general.html`, `marcas.html` | ✅ |
| `Layout/AcordeonPage.ss` + `TarjetaPage.ss` + `TarjetaSimplePage.ss` | `tarjetas/lista.html`, `acordeon.html` | ⚠️ falta tarjeta simple |
| `Layout/CalendarioPage.ss` + `Includes/ActividadesMes.ss` | — | ❌ no existe |
| `Layout/ArchivoPage.ss` + `ArchivoDesplegablePage.ss` | — | ❌ no existe |
| `Layout/DocumentoTemplate.ss` | — | ❌ no existe |
| `Layout/RevistaPage.ss` + `CodepiNoticiaPage.ss` + `GestorEnlacesPage.ss` | — | ❌ no existen, todos redirigen a `noticias:lista` |
| `Layout/DiaPIPage.ss` + `ProtegeLoTuyoPage.ss` + `ConcursoJuventudPage.ss` | — | ❌ no existen |
| `Includes/Header.ss` | inline en `base.html` | ✅ aplanado |
| `Includes/Footer.ss` | inline en `base.html` | ✅ aplanado |
| `Includes/BreadCrumbs.ss` | — | ❌ no se ve breadcrumb dinámico |
| `Includes/Slider.ss`, `Banners.ss`, `NoticiasInclude.ss`, `ContactoInclude.ss`, `FormularioContacto.ss`, `MensajeExitoFormulario.ss`, `HeaderImage.ss`, `ImagesModals.ss`, `PortfolioModalsIndex.ss` | — | ❌ ninguno migrado |
| `Email/MensajeContacto.ss`, `MensajeSuscripcion.ss`, `TablaForm.ss`, `VistaFormularioGenerico.ss`, `VistaSolicitudVisita.ss` | `contacto/email_mensaje.html` | ⚠️ uno solo migrado |

### 2.2 Lógica de templates → views/templatetags

✅ Bien movida:
- `Page_Controller::ListaNoticiasDestacadas` → `Noticia.noticias_destacadas()` classmethod usado en `NoticiaListView` y `home_view`. Idiomatic.
- `getEpigrafe($texto)` → `Noticia.get_epigrafe()` y `Biblioteca.get_epigrafe()` como métodos de modelo. Correcto.
- `Header.ss` con 3 niveles de `<% loop Children %>` → `apps.menus.context_processors.menu_popup_context` con `_flatten_descendants` recursivo y `paginas_activas_por_legacy` dict. **Solución bien resuelta** considerando que no se usó django-mptt/django-treebeard.
- `MenuDerecho.getHijos()` → agrupación de padres/hijos en el mismo context_processor. OK.
- `get_permalink($id)` por TreeDropdownField → `_resolve_pagina_url(pagina)` que mapea `TipoPagina` → `reverse(...)`. Razonable.
- `ListaNoticiasBuscador` → `NoticiaListView.get_queryset` con `Q(titulo__icontains) | Q(contenido__icontains)`. Correcto (más seguro que el SQL crudo del original).
- `<% if Anexo %>$Anexo.URL <% end_if %>` → `{% if pagina.anexo %}{{ pagina.anexo.url }}{% endif %}`. Mapeo trivial.

⚠️ Mal o incompletamente movida:
- **`Biblioteca` búsqueda**: el `BibliotecaPageController` original ejecutaba SQL crudo con `LIKE` sobre `Titulo`, `Descripcion`, `Categoria.Categoria`, `Etiqueta.Etiqueta`. La `BibliotecaListView` Django sólo hace `titulo__icontains`. Se perdió búsqueda por descripción/categoría/etiqueta.
- **`TemaEje` con `ListaTemasDeEjes(eje)`**: en lugar de modelar `TemaEje` y poblar desde la BD, la home tiene los 3 ejes con sus ítems hardcoded en `home_view.ejes_home` apuntando a URLs `https://www.dinapi.gov.py/portal/v3/...` (¡es decir, redirigiendo al sitio viejo!). Esto rompe la independencia del nuevo sitio.
- **`SiteConfig.MostrarPopUp` con cookie semanal**: en el original, el popup se muestra basado en SiteConfig + cookie con expiry 7 días. En Django se reemplazó con `Popup.objects.filter(activo=True)` y `sessionStorage`. Funcionalmente similar pero con scope distinto (la cookie persiste entre sesiones, sessionStorage no).
- **`ObtenerLogo`**: hardcoded a `{% static 'img/header/logo_nacional.png' %}`. Ignora `SiteConfig.logo` aunque el modelo tiene un `ImageField`. Se puede arreglar fácil pero hoy está roto.
- **`Breadcrumbs`** del original (basados en `$Level(2)` y la jerarquía SiteTree) no se reprodujeron en Django.

❌ No movida en absoluto:
- `submit2`, `enviarFormulario`, `enviarFormularioSuscripcion`: la lógica del form de suscripción al boletín no existe.
- `convertirNumero`: utility para WhatsApp — el original referenciaba `Telefono::get()` que era una clase huérfana, así que probablemente sea código muerto del SS (acepable no migrarlo).
- `ListaSucursales`, `ListaPreguntasFrecuentes`, `ListaEnlacesUtiles`, `ListaNumerosWhatsapp` — referencias a clases huérfanas, lo correcto es no migrarlas.
- `CalendarioPage_Controller::FiltrarPorMes`, `DelDia`, `MesActual`, `Calendarios`, `ActividadesDelMes`, `ListarTodasActividades`, `MesActualNro` → app calendario no existe.

---

## 3. BASE DE DATOS / MIGRACIONES

### 3.1 Estado de migraciones

Las migraciones existen y son consistentes:
- `core`: 3 migraciones (`0001_initial`, `0002_pagina`, `0003_pagina_legacy_id_pagina_parent_legacy_id_and_more`).
- `noticias`, `contacto`, `biblioteca`, `concursos`, `boletines`, `tarjetas`, `menus`: 1 migración cada una (`0001_initial`).

Generadas por Django 5.2.12 entre 2026-03-30 y 2026-04-08.

### 3.2 Veredicto migraciones

✅ Las migraciones generadas reflejan correctamente los modelos definidos. **No hay desincronización modelos↔migraciones**. Tipos correctos (`PositiveIntegerField`, `SlugField`, `ImageField`, `FileField`, `DateField`, `BooleanField`, `ForeignKey` con `on_delete`).

❌ Las migraciones reflejan correctamente lo que está, pero **lo que está es incompleto**:
- Faltan tablas pivote para Biblioteca M2M.
- Faltan tablas para Calendario, Actividad, Anuncio, Carousel, EnlaceInteres, MensajeReclamos, EtiquetaBiblioteca, Documento, Archivo, ArchivoPage, ArchivoDesplegablePage, TarjetaSimple, TemaEje.

⚠️ **Riesgo de producción**: `DATABASES.ENGINE = sqlite3`. La BD productiva original es MySQL y Django debería usar MySQL (o Postgres). Cambiar el engine al final exige re-correr todas las migraciones — no debería romper nada pero es un paso pendiente. Las migraciones son SQL-agnósticas, así que es portable.

---

## 4. LÓGICA DE NEGOCIO

### 4.1 Portado correctamente

✅ Datos legacy importados con management commands específicos (estado declarado en README, verificado en `apps/noticias/management/commands/import_silverstripe_noticias.py`):

| Dataset | Cantidad declarada | Comando |
|---|---|---|
| Noticias | 575 | `import_silverstripe_noticias` |
| CategoriaNoticia | 5 | (mismo) |
| Páginas (SiteTree) | 512 | `import_silverstripe_paginas` |
| Concursos | 24 | `import_silverstripe_concursos` |
| Biblioteca | 279 | `import_silverstripe_biblioteca` |
| CategoriaBiblioteca | 11 | (mismo) |
| Boletines | 1208 | `import_silverstripe_boletines` |
| Periodos boletines | 109 | (mismo) |
| Tarjetas | 47 (en 14 páginas) | `import_silverstripe_tarjetas_acordeon` |
| AcordeonPages / Items | 19 / 22 | (mismo) |

El comando de noticias parsea regex sobre el dump SQL (`INSERT_RE`) — solución pragmática que funciona; revisable si hace falta robustez.

✅ Lógica de negocio portada en views/models:
- Listado y búsqueda de noticias (`NoticiaListView`, `buscar_noticias`).
- Detalle de noticias con relacionadas (`NoticiaDetailView`).
- Listado de biblioteca con filtro por categoría y búsqueda por título (`BibliotecaListView`).
- Detalle de biblioteca (`BibliotecaDetailView`).
- Boletines agrupados por período y tipo (`BoletinGeneralListView`, `BoletinMarcaListView`).
- Concursos agrupados por año (`ConcursoListView`).
- Tarjetas y acordeón agrupados por página (`TarjetaPageListView`, `AcordeonPageListView`).
- Form de contacto con email vía `django.core.mail.send_mail` (`contact_form_view`).
- Construcción de menú jerárquico con `parent_legacy_id` (`menus/context_processors.py`).
- Resolución de URLs por TipoPagina (`_resolve_pagina_url`).
- Cards institucionales armadas con heurística de tokens (`_build_institucional_cards`).

### 4.2 No portada — agujeros funcionales reales

❌ **Reclamos**: el form de `ReclamosPage::Formulario` con 10 temas, `RandomNameUploadField` (renombrado SHA256), validación anti-bypass de PDF, envío con adjunto a `reclamos@dinapi.gov.py` — nada de esto existe en Django. Es la pieza pendiente más visible para usuarios externos.

❌ **Calendario / Actividades**: ni modelo ni views ni templates. `CalendarioPage_Controller` con su filtro AJAX por mes (`FiltrarPorMes`, `DelDia`) está totalmente sin migrar.

❌ **Búsqueda en biblioteca**: degradada de SQL crudo con 4 LIKE (Título/Descripción/Categoría/Etiqueta) a sólo título.

❌ **Búsqueda en documentos** (`DocumentoController` con `titulo`, `desde`, `hasta`): sin migrar.

❌ **Form de suscripción al boletín**: `enviarFormularioSuscripcion` con PHPMailer manual — sin migrar (probablemente ok si el form no se usaba).

❌ **Carousel/Slider de portada**: en el original había `<% loop $ListaCarousel %>` con CRUD desde CMS. La home de Django tiene noticias destacadas pero no carousel dinámico.

❌ **Anuncios** (`Anuncio`) y **Enlaces de Interés** (`EnlaceInteres`): bloques editables desde CMS, sin migrar.

❌ **Ejes y temas** (`TemaEje`): hardcoded en `home_view.ejes_home`, apuntando a URLs del sitio viejo `https://www.dinapi.gov.py/portal/v3/...`.

❌ **SiteConfig efectivo**: el modelo existe pero ningún template lo consume; emails, teléfono, dirección y links del footer están hardcoded en `base.html`.

❌ **Breadcrumbs jerárquicos**: el original tenía `$Breadcrumbs` calculado con `Level(2)` por toda la jerarquía. Django no lo reproduce.

❌ **Versioned (Stage/Live)**: no implementado, esperable según el inventario inicial.

❌ **`?stage=Stage` legacy URLs**: el footer tiene links a `https://www.dinapi.gov.py/portal/v3/...?stage=Stage` — está apuntando al sitio viejo.

---

## VEREDICTO FINAL

### **CONTINUAR la migración actual.** Empezar de cero sería un error.

#### Justificación

1. **Hay datos importados que no se pueden tirar**: 575 noticias, 512 páginas con jerarquía SiteTree preservada, 1208 boletines, 279 entradas de biblioteca, 24 concursos, 47 tarjetas, 22 ítems de acordeón. El esfuerzo de ETL ya hecho (5 management commands con parser de dumps SQL de SilverStripe) es la parte más tediosa de cualquier migración y está terminada para el 80% del contenido.

2. **Las decisiones arquitectónicas centrales son correctas**:
   - Unificación de los 4 modelos clónicos `BoletinGeneral/Logotipos/Movimientos/MarcasDocumentos` en un solo `Boletin` con discriminador `tipo` — exactamente lo que recomendé en el inventario inicial.
   - Unificación de los ~25 tipos de página de SiteTree en un único `Pagina` con `TipoPagina` enum + `legacy_id`/`parent_legacy_id` — pragmático y suficiente para un sitio mayormente estático.
   - Separación en 8 apps por dominio (no monolito).
   - Patrón consistente `legacy_id`/`legacy_created` para trazabilidad e idempotencia de imports.
   - Uso de `context_processor` para menú global, CBVs (`ListView`/`DetailView`/`TemplateView`) en lugar de FBVs masivos, `prefetch_related` donde corresponde, indexes en modelos.

3. **El ~70% del sitio público funciona ya**: home, listado y detalle de noticias, biblioteca con filtros, boletines agrupados, concursos por año, tarjetas, acordeón, contacto con email. La parte pendiente es identificable, acotada y no exige rediseño.

4. **La calidad del código existente es razonable**. No hay anti-patrones graves: views CBV estándar, models con métodos sensatos, sin SQL crudo (a diferencia del original), forms con `ModelForm`, templates con `extends`, `{% url %}` y `{% static %}`. No hay deuda técnica que justifique tirar.

5. **Lo que falta es trabajo nuevo, no corrección masiva**. Los modelos y templates ausentes no implican rehacer lo hecho — implica agregar.

#### Empezar de cero **costaría más** que continuar:
- Re-escribir 5 management commands de import desde dumps SQL (días de trabajo).
- Re-discutir y re-tomar las decisiones de arquitectura.
- Reproducir los 19 templates ya estilizados.
- Re-validar 575 noticias / 1208 boletines a nivel datos.

---

## Plan de corrección priorizado

### P0 — Bloqueantes para producción (no se puede salir vivo sin esto)

1. **Mover credenciales a `.env`**. Hoy `SECRET_KEY`, `EMAIL_HOST_PASSWORD = 'N0reply.com'` están en código. `python-decouple` ya está en requirements pero no se usa.
2. **Cambiar `DATABASES.ENGINE` a MySQL o Postgres** y re-correr migraciones contra la BD real. Sqlite no aguanta producción de un sitio gubernamental.
3. **`DEBUG = False`** y configurar `ALLOWED_HOSTS` solo con dominios reales.
4. **Crear app `reclamos`** con modelo `MensajeReclamos`, form con 10 temas, `FileField` para adjunto con renombrado seguro (sha256 como el original), validación anti-bypass de PDF, vista `submit` que envíe a `reclamos@dinapi.gov.py`. Es la funcionalidad pública más visible que falta.
5. **Reemplazar URLs hardcoded a `https://www.dinapi.gov.py/portal/v3/...?stage=Stage`** en `home_view.ejes_home`, `banners_institucionales`, `banners_servicios` y en el footer de `base.html`. Hoy el sitio nuevo redirige al viejo, lo cual rompe el propósito de la migración.

### P1 — Cubrir el resto del sitio público

6. **Crear app `calendario`** con `Calendario` y `Actividad`, vista `CalendarioPageView` con filtro mensual y endpoint AJAX (`DelDia`), templates `calendario/index.html` y `calendario/actividades_mes.html` (parcial). 
7. **Agregar a `biblioteca`**: `EtiquetaBiblioteca` y los 4 `ManyToManyField` (Videos, Imagenes, Documentos, Etiquetas) con migración nueva. Re-importar M2M desde el dump (pivot tables `Biblioteca_Videos`/`Biblioteca_Imagenes`/`Biblioteca_Documentos`/`Biblioteca_Etiquetas`).
8. **Mejorar búsqueda en `BibliotecaListView`** con `Q(titulo__icontains) | Q(descripcion__icontains) | Q(categoria__nombre__icontains) | Q(etiquetas__nombre__icontains)`.
9. **Crear app `home_blocks`** (o agregar a `core`/`menus`): modelos `Anuncio`, `Carousel`, `EnlaceInteres` con migración + admin + consumo en `home_view`/`base.html`.
10. **Modelar `TemaEje`** y reemplazar `home_view.ejes_home` hardcoded por consulta DB. Comando de import desde el dump.
11. **Hacer que el footer y logo consuman `SiteConfig`** vía `context_processor` global (`core.context_processors.site_config`). Hoy el modelo existe pero está en desuso.
12. **Implementar `Breadcrumbs`** como template tag basado en `Pagina.parent_legacy_id`.

### P2 — Calidad y cierre

13. **Cambiar `Pagina.parent_legacy_id` a `models.ForeignKey('self', null=True, blank=True, on_delete=SET_NULL)`** (con migración de datos) o adoptar `django-treebeard`/`django-mptt`. Hoy es un Int suelto.
14. **Cambiar `Concurso.pagina_legacy_id` a `ForeignKey(Pagina)`** real.
15. **Modelo `Documento`** con búsqueda por `titulo`, `desde`, `hasta` (mapear `DocumentoController`).
16. **Modelo `Archivo` + páginas `ArchivoPage`/`ArchivoDesplegablePage`** + templates.
17. **`MensajeContacto.TEMAS_CHOICES`** ampliado a los 10 temas reales (o consolidar con `MensajeReclamos`).
18. **Editor WYSIWYG** para `Noticia.contenido`, `Acordeon.contenido`, `Biblioteca.descripcion` y `SiteConfig.contenido_biblioteca`. Sugerencia: `django-tinymce` o `django-ckeditor-5`.
19. **Templates faltantes para tipos de página secundarios**: `RevistaPage` (lista de revistas con PDF), `CodepiNoticiaPage`, `GestorEnlacesPage`, `DiaPIPage`, `ProtegeLoTuyoPage`, `ConcursoJuventudPage`. Hoy todos redirigen a `noticias:lista` por `_resolve_pagina_url`, lo cual es incorrecto.
20. **Modelos `TarjetaSimple`/`TarjetaSimplePage`**.

### P3 — Nice to have

21. **Versioned (Draft/Live)** si el equipo editorial lo necesita: `django-reversion` o flag `is_published` con `Manager` custom.
22. **Búsqueda full-text seria** con `django.contrib.postgres.search.SearchVector` (si se migra a Postgres) o `django-haystack` + Meilisearch/Elasticsearch.
23. **Tests** — actualmente `tests.py` están vacíos en todas las apps.
24. **Comando único `import_silverstripe_all`** que oriqueste los 5 imports existentes + los nuevos.
25. **`media/legacy/` cleanup**: hoy hay copia entera de los assets del SS dentro del proyecto Django; mover a una rotación regular.

---

## Apéndice — Ranking de hallazgos por gravedad

| # | Hallazgo | Gravedad |
|---|---|---|
| 1 | Credenciales y SECRET_KEY hardcoded en `settings.py` | 🔴 Crítico |
| 2 | `DATABASES = sqlite3` en lugar de MySQL/Postgres | 🔴 Crítico |
| 3 | `DEBUG = True`, `ALLOWED_HOSTS = ['*.dinapi.gov.py']` | 🔴 Crítico |
| 4 | Sin app `reclamos` (MensajeReclamos + form 10 temas + adjunto) | 🟠 Alto |
| 5 | Home y banners apuntan a URLs del sitio viejo `?stage=Stage` | 🟠 Alto |
| 6 | Biblioteca pierde `EtiquetaBiblioteca` y los 4 ManyToManyField | 🟠 Alto |
| 7 | Sin app `calendario` (Calendario/Actividad) | 🟠 Alto |
| 8 | `TemaEje` hardcoded en home_view en lugar de modelo | 🟡 Medio |
| 9 | `SiteConfig` modelo existe pero templates no lo consumen | 🟡 Medio |
| 10 | Búsqueda biblioteca degradada (sólo título) | 🟡 Medio |
| 11 | Sin app `Anuncio`/`Carousel`/`EnlaceInteres` para home | 🟡 Medio |
| 12 | `Pagina.parent_legacy_id` como Int en lugar de FK self | 🟡 Medio |
| 13 | `Concurso.pagina_legacy_id` como Int en lugar de FK | 🟡 Medio |
| 14 | Sin breadcrumbs jerárquicos | 🟢 Bajo |
| 15 | Sin tests | 🟢 Bajo |
| 16 | Sin editor WYSIWYG para HTMLText | 🟢 Bajo |
| 17 | Templates faltantes para tipos de página secundarios | 🟢 Bajo |
| 18 | Sin Versioned (Stage/Live) | 🟢 Bajo (esperable) |
