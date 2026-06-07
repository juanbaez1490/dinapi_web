"""
Orquestador de re-importacion completa desde un dump SQL legacy.

Corre la pipeline en orden:
  1. Backup de db.sqlite3 (a menos que se pase --skip-backup)
  2. import_silverstripe_paginas      (core.Pagina - base de todo)
  3. import_silverstripe_tarjetas_acordeon  (TarjetaPage, Tarjeta, AcordeonPage, AcordeonItem)
  4. import_silverstripe_noticias     (CategoriaNoticia, Noticia)
  5. import_silverstripe_boletines    (PeriodoBoletin, Boletin)
  6. import_silverstripe_biblioteca   (Biblioteca, Documento, Categoria, Etiqueta)
  7. import_biblioteca_relaciones     (M2M biblioteca)
  8. import_silverstripe_concursos    (Concurso)
  9. import_silverstripe_menus_popups (MenuDerecho, Popup)
 10. import_home_bloques              (TemaEje, CarouselItem, Anuncio, EnlaceInteres)
 11. reparar_bs5_attrs                (data-toggle -> data-bs-toggle)
 12. reparar_acordeones               (FK huerfanas AcordeonItem)
 13. reparar_tarjetas                 (FK huerfanas Tarjeta)
 14. validate_migration --skip-mysql  (sanity check final)

Uso:
    # Dry-run (default) - solo simula
    python manage.py reimportar_legacy

    # Apply - corre la pipeline completa
    python manage.py reimportar_legacy --apply

    # Apply + truncar tablas legacy antes de re-importar
    python manage.py reimportar_legacy --apply --truncate

    # SQL en otra ruta
    python manage.py reimportar_legacy --sql=otro_dump.sql --apply

NOTAS DE SEGURIDAD:
- Sin --apply, ningun comando hace cambios reales.
- Con --apply, se hace backup automatico de db.sqlite3 antes de tocar nada.
- --truncate borra las tablas legacy antes de cargar (mas limpio, pero pierde
  ediciones manuales del admin sobre las mismas tablas).
- Los comandos `reparar_*` son idempotentes: correrlos dos veces no hace dano.
"""
import shutil
import time
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.core.management.base import BaseCommand


# Pipeline: (label, command_name, kwargs_extra)
# Todos aceptan --sql-path, --dry-run, --truncate (excepto reparar_* y validate_*)
IMPORT_STEPS = [
    ('Paginas (SiteTree)',    'import_silverstripe_paginas',          {}),
    ('Tarjetas y Acordeones', 'import_silverstripe_tarjetas_acordeon', {}),
    ('Noticias',              'import_silverstripe_noticias',         {}),
    ('Boletines',             'import_silverstripe_boletines',        {}),
    ('Biblioteca',            'import_silverstripe_biblioteca',       {}),
    ('Biblioteca M2M',        'import_biblioteca_relaciones',         {'truncate_kwarg': 'truncate_relaciones'}),
    ('Concursos',             'import_silverstripe_concursos',        {}),
    ('Menus y Popups',        'import_silverstripe_menus_popups',     {}),
    ('Home (TemaEje, etc)',   'import_home_bloques',                  {}),
]

# Comandos de reparacion (post-import). Idempotentes.
REPAIR_STEPS = [
    ('BS4 -> BS5 attrs',         'reparar_bs5_attrs',  {}),
    ('FK AcordeonItem huerfanos', 'reparar_acordeones', {'use_sql_arg': '--sql'}),
    ('FK Tarjeta huerfanas',     'reparar_tarjetas',   {'use_sql_arg': '--sql'}),
]


class Command(BaseCommand):
    help = 'Re-importa todo el contenido legacy desde un dump SQL fresco y corre las reparaciones.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql', default='bd_legacy_bk_dinapi_2026-06-05.sql',
            help='Ruta al SQL legacy (relativa al BASE_DIR o absoluta). '
                 'Default: bd_legacy_bk_dinapi_2026-06-05.sql',
        )
        parser.add_argument(
            '--apply', action='store_true',
            help='Aplica los cambios. Sin esta flag corre en dry-run.',
        )
        parser.add_argument(
            '--truncate', action='store_true',
            help='Trunca las tablas legacy antes de re-importar. '
                 'Mas limpio, pero borra ediciones manuales sobre esas tablas.',
        )
        parser.add_argument(
            '--skip-backup', action='store_true',
            help='No copia db.sqlite3 a un .bak antes de aplicar. Solo si sabes lo que haces.',
        )
        parser.add_argument(
            '--skip-validate', action='store_true',
            help='No corre validate_migration al final.',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        truncate = options['truncate']
        skip_backup = options['skip_backup']
        skip_validate = options['skip_validate']

        sql_path = Path(options['sql'])
        if not sql_path.is_absolute():
            sql_path = Path(settings.BASE_DIR) / sql_path
        sql_path = sql_path.resolve()

        if not sql_path.exists():
            raise CommandError(f'No existe el SQL: {sql_path}')

        size_mb = sql_path.stat().st_size / (1024 * 1024)
        self.stdout.write(self.style.HTTP_INFO(
            f'\n{"=" * 70}\nRE-IMPORTACION LEGACY DINAPI\n{"=" * 70}'
        ))
        self.stdout.write(f'SQL:       {sql_path}  ({size_mb:.1f} MB)')
        self.stdout.write(f'Modo:      {"APLICAR" if apply else "DRY-RUN"}')
        self.stdout.write(f'Truncate:  {"SI" if truncate else "NO"}')
        self.stdout.write(f'Backup:    {"NO (skip)" if skip_backup else "SI"}')
        self.stdout.write(f'Validate:  {"NO (skip)" if skip_validate else "SI"}\n')

        # --- 1. Backup ---
        if apply and not skip_backup:
            self._backup_sqlite()
        elif not apply:
            self.stdout.write(self.style.WARNING(
                '[dry-run] Sin --apply ningun comando hace cambios reales.\n'
            ))

        # --- 2-10. Imports ---
        self._section('IMPORT')
        for i, (label, cmd, extra) in enumerate(IMPORT_STEPS, start=1):
            self._run_import(i, label, cmd, extra, sql_path, apply, truncate)

        # --- 11-13. Reparaciones (solo si apply) ---
        if apply:
            self._section('REPARACIONES POST-IMPORT')
            for i, (label, cmd, extra) in enumerate(REPAIR_STEPS, start=1):
                self._run_repair(i, label, cmd, extra, sql_path)

        # --- 14. Validacion ---
        if apply and not skip_validate:
            self._section('VALIDACION FINAL')
            try:
                call_command('validate_migration', skip_mysql=True)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'validate_migration fallo: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n{"=" * 70}\n{"PIPELINE COMPLETA" if apply else "DRY-RUN COMPLETO"}\n{"=" * 70}\n'
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                'Sin cambios reales. Re-ejecuta con --apply para aplicar.\n'
            ))

    # -----------------------------------------------------------------

    def _section(self, title):
        self.stdout.write(self.style.HTTP_INFO(f'\n--- {title} ---'))

    def _backup_sqlite(self):
        db_path = Path(settings.DATABASES['default']['NAME'])
        if not db_path.exists():
            self.stdout.write(self.style.WARNING(
                f'  (db no es SQLite o no existe en {db_path}, salteando backup)'
            ))
            return
        stamp = time.strftime('%Y%m%d-%H%M%S')
        bak = db_path.with_suffix(db_path.suffix + f'.bak-{stamp}')
        shutil.copy2(db_path, bak)
        size_mb = bak.stat().st_size / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(
            f'  Backup: {bak.name}  ({size_mb:.1f} MB)\n'
        ))

    def _run_import(self, idx, label, cmd, extra, sql_path, apply, truncate):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n[{idx}/{len(IMPORT_STEPS)}] {label}  ({cmd})'
        ))
        kwargs = {'sql_path': str(sql_path)}
        if not apply:
            kwargs['dry_run'] = True
        if apply and truncate:
            # algunos comandos usan un nombre de flag distinto al default 'truncate'
            kwargs[extra.get('truncate_kwarg', 'truncate')] = True

        try:
            buffer = StringIO()
            call_command(cmd, stdout=buffer, **kwargs)
            output = buffer.getvalue().strip()
            # mostramos solo lineas relevantes para no saturar
            for line in output.splitlines()[-10:]:
                self.stdout.write(f'  {line}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  FALLO: {e}'))
            self.stdout.write(self.style.WARNING(
                f'  (continuando con los siguientes pasos)'
            ))

    def _run_repair(self, idx, label, cmd, extra, sql_path):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n[{idx}/{len(REPAIR_STEPS)}] {label}  ({cmd})'
        ))
        kwargs = {'apply': True}
        if extra.get('use_sql_arg'):
            kwargs['sql'] = str(sql_path)

        try:
            buffer = StringIO()
            call_command(cmd, stdout=buffer, **kwargs)
            output = buffer.getvalue().strip()
            for line in output.splitlines()[-8:]:
                self.stdout.write(f'  {line}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  FALLO: {e}'))
