"""
Repara el FK `Biblioteca.categoria` desde el SQL legacy.

Tabla legacy Biblioteca tiene CategoriaID (columna 11 del schema) que apunta
a CategoriaBiblioteca.ID legacy. En Django ni Biblioteca ni CategoriaBiblioteca
tienen un campo legacy_id explicito, pero ambos slugs siguen el patron
`<slugify(titulo)>-<legacy_id>`.

Estrategia:
  1. Construir map CategoriaBiblioteca: legacy_id (del slug) -> instance.
  2. Construir map Biblioteca: legacy_id (del slug) -> instance.
  3. Parsear (ID, CategoriaID) del SQL legacy de Biblioteca.
  4. Asignar Biblioteca.categoria_id.

Uso:
    python manage.py reparar_categorias_biblioteca               # dry-run
    python manage.py reparar_categorias_biblioteca --apply
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.management._sql_parser import iter_insert_tuples
from apps.biblioteca.models import Biblioteca, CategoriaBiblioteca


SLUG_LEGACY_RE = re.compile(r'-(\d+)$')


class Command(BaseCommand):
    help = 'Asocia Biblioteca.categoria leyendo CategoriaID desde el SQL legacy.'

    def add_arguments(self, parser):
        parser.add_argument('--sql', default=None,
            help='Ruta al SQL legacy. Default: <BASE_DIR>/bd_legacy_bk_dinapi_2026-06-05.sql')
        parser.add_argument('--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en dry-run.')

    def handle(self, *args, **options):
        apply = options['apply']
        sql_path = Path(options['sql'] or Path(settings.BASE_DIR) / 'bd_legacy_bk_dinapi_2026-06-05.sql')
        if not sql_path.exists():
            raise CommandError(f'No existe el SQL: {sql_path}')

        sql_text = sql_path.read_text(encoding='utf-8', errors='replace')

        # Maps legacy_id -> Django instance, extrayendo del sufijo del slug
        def extract_legacy_id(slug):
            m = SLUG_LEGACY_RE.search(slug or '')
            return int(m.group(1)) if m else None

        cat_by_legacy = {}
        for c in CategoriaBiblioteca.objects.all():
            lid = extract_legacy_id(c.slug)
            if lid is not None:
                cat_by_legacy[lid] = c
        self.stdout.write(f'CategoriaBiblioteca indexadas por legacy_id: {len(cat_by_legacy)}')

        bib_by_legacy = {}
        for b in Biblioteca.objects.all():
            lid = extract_legacy_id(b.slug)
            if lid is not None:
                bib_by_legacy[lid] = b
        self.stdout.write(f'Biblioteca indexadas por legacy_id: {len(bib_by_legacy)}\n')

        # Schema Biblioteca: 0=ID, ..., 10=ImagenPrincipalID, 11=CategoriaID
        asignadas = 0
        sin_cat_legacy = 0
        sin_bib_django = 0
        ya_ok = 0

        with transaction.atomic():
            for t in iter_insert_tuples(sql_text, 'Biblioteca'):
                if len(t) < 12:
                    continue
                bib_legacy_id = t[0]
                cat_legacy_id = t[11]

                bib = bib_by_legacy.get(bib_legacy_id)
                if not bib:
                    sin_bib_django += 1
                    continue
                if not cat_legacy_id:
                    continue
                cat = cat_by_legacy.get(cat_legacy_id)
                if not cat:
                    sin_cat_legacy += 1
                    continue
                if bib.categoria_id == cat.id:
                    ya_ok += 1
                    continue

                if apply:
                    Biblioteca.objects.filter(pk=bib.pk).update(categoria=cat)
                asignadas += 1

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\nResumen:\n'
            f'  Asignadas:                    {asignadas}\n'
            f'  Ya estaban correctas:         {ya_ok}\n'
            f'  Sin Biblioteca en Django:     {sin_bib_django}\n'
            f'  Sin Categoria matcheable:     {sin_cat_legacy}\n'
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                'Sin cambios persistidos. --apply para guardar.'
            ))
