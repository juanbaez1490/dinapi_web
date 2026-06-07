# Migracion SilverStripe 3.4 -> Django

## Estado actual

- Proyecto SilverStripe origen disponible en `dinapi_web_old`.
- Django ya tiene apps iniciales: `core`, `noticias`, `contacto`, `biblioteca`, `tarjetas`, `menus`.
- Se implemento base para tipos de pagina en `apps.core.Pagina`.

## Tipos de pagina detectados en SilverStripe

Clases encontradas con `extends Page` o su controlador equivalente:

- HomePage
- GeneralPage
- InstitucionalPage
- ContactPage
- NoticiaPage
- RevistaPage
- GestorEnlacesPage
- CodepiNoticiaPage
- BibliotecaPageController (ruta/controlador especifico)
- ConcursosPage
- ReclamosPage
- ArchivoPage
- ArchivoDesplegablePage
- AcordeonPage
- TarjetaPage
- TarjetaSimplePage
- CalendarioPage
- BoletinPage
- PeriodoBoletinPage
- BoletinMarcaPage
- PeriodoBoletinMarcaPage
- PeriodoBoletinMarcaGenericoPage
- ProtegeLoTuyoPage
- DiaPIPage
- ConcursoJuventudPage

## Noticias: origen y mapeo

Origen SilverStripe:

- `mysite/code/Noticias/Noticia.php`
- `mysite/code/Noticias/CategoriaNoticia.php`
- `mysite/code/Noticias/NoticiaPage.php`
- `mysite/code/Noticias/NoticiaDetalleController.php`
- `themes/dinapi/templates/Layout/NoticiaPage.ss`
- `themes/dinapi/templates/Layout/NoticiaDetalle.ss`

Destino Django inicial:

- `apps/noticias/models.py`
- `apps/noticias/views.py`
- `apps/noticias/urls.py`
- `templates/noticias/lista.html`
- `templates/noticias/detalle.html`
- `templates/noticias/destacadas.html`
- `templates/noticias/busqueda.html`

## Orden recomendado para migracion completa

1. Core navegacion y tipado de paginas (hecho base).
2. Noticias y revista (en progreso).
3. Contacto y reclamos.
4. Biblioteca y detalle de biblioteca.
5. Concursos y detalle de concurso.
6. Boletines (incluye marcas/genericos).
7. Tarjetas y acordeon.
8. Calendario/actividades.
9. Menus, popups, carousel y componentes home.
10. Importacion de datos y medios historicos.

## Proxima iteracion sugerida

- Crear comando de importacion para `CategoriaNoticia` y `Noticia` desde origen SilverStripe.
- Migrar `NoticiaDetalleController` y layout para equivalencia visual.
- Modelar tipos faltantes con comportamiento especifico por seccion.

## Comandos de importacion implementados

- Noticias y categorias:
	- `python manage.py import_silverstripe_noticias --sql-path dinapi_web_old/dinapi.sql --truncate`
- Tipos de paginas (SiteTree):
	- `python manage.py import_silverstripe_paginas --sql-path dinapi_web_old/dinapi.sql --truncate`

Ambos comandos aceptan `--dry-run` para validar sin escribir datos.

## Resultado de importacion actual

- Noticias importadas: 575
- Categorias de noticias: 5
- Paginas importadas (tipos de pagina): 512
- Concursos importados: 24

## Comando de importacion de concursos

- `python manage.py import_silverstripe_concursos --sql-path dinapi_web_old/dinapi.sql --truncate`


## Comandos de importacion adicionales (ejecutados 2026-04-08)

- Biblioteca:
- `python manage.py import_silverstripe_biblioteca --sql-path dinapi_web_old/dinapi.sql --truncate`
- Boletines:
- `python manage.py import_silverstripe_boletines --sql-path dinapi_web_old/dinapi.sql --truncate`
- Tarjetas y Acordeon:
- `python manage.py import_silverstripe_tarjetas_acordeon --sql-path dinapi_web_old/dinapi.sql --truncate`

## Resultado de importacion actualizado (2026-04-08)

- Noticias importadas: 575
- Categorias de noticias: 5
- Paginas importadas: 512
- Concursos importados: 24
- Biblioteca: 279 items, 11 categorias
- Boletines: 1208 registros, 109 periodos
- Tarjetas: 47 tarjetas en 14 paginas; AcordeonPage: 19 paginas, 22 items

## Menu legacy (Header) migrado a Django (2026-04-08)

- `Pagina` ahora guarda jerarquia de SiteTree con `legacy_id` y `parent_legacy_id`.
- El importador de paginas actualiza por `legacy_id` (fallback por slug) y conserva relacion padre/hijo.
- La barra de navegacion principal se arma desde DB con grupos jerarquicos (equivalente funcional de `$Menu(1)`).
- El menu derecho se mantiene desde `MenuDerecho` y se limpiaron titulos con comillas heredadas del parseo SQL.
- Verificacion runtime del context processor:
  - principal: 1 item simple + 3 grupos
  - derecho: 1 item simple + 1 grupo

## Estado por paso (2026-04-08)

| Paso | Estado | Descripcion |
|------|--------|-------------|
| 1 | Hecho | Core navegacion, tipos de pagina, menus dinamicos |
| 2 | Hecho | Noticias 575 + 5 cat, templates lista/detalle rediseñados al estilo SS |
| 3 | Pendiente | Contacto (form OK), Reclamos (pendiente modelo dedicado) |
| 4 | Hecho | Biblioteca 279/11 cat, template lista rediseñado al estilo SS |
| 5 | Hecho | Concursos 24 importados, templates basicos |
| 6 | Hecho | Boletines 1208/109 periodos importados |
| 7 | Hecho | Tarjetas 47 y Acordeon 22 items importados |
| 8 | Pendiente | Calendario/actividades (sin modelo aun) |
| 9 | Pendiente | popup/carousel home pendiente de refinamiento |
| 10 | En curso | Imagenes legacy no migradas (media/legacy/) |

## Proxima iteracion sugerida

- Crear vistas y templates para TarjetaPage (visor de tarjetas).
- Crear vistas y templates para AcordeonPage (acordeon desplegable).
- Agregar vista de Reclamos o extender contacto.
- Migrar imagenes de noticias/biblioteca desde rutas legacy.
- Refinar template de concursos con imagenes y detalle.
