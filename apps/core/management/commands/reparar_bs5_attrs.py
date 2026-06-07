"""
Reparar atributos Bootstrap 4 -> Bootstrap 5 en HTML migrado de SilverStripe.

El contenido HTML guardado en Pagina.contenido viene del SilverStripe legacy
y usa los atributos de Bootstrap 4:

    <h4 data-toggle="collapse" data-target="#colapse-11">...</h4>

El sitio Django renderiza con Bootstrap 5, que requiere data-bs-toggle y
data-bs-target. Sin reemplazo, los acordeones quedan permanentemente
colapsados y el usuario no puede abrirlos.

Uso:
    python manage.py reparar_bs5_attrs                  # dry-run (default)
    python manage.py reparar_bs5_attrs --apply          # aplica y guarda
    python manage.py reparar_bs5_attrs --slug=foo --apply  # solo una pagina
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Pagina


REPLACEMENTS = [
    (re.compile(r'\bdata-toggle='), 'data-bs-toggle='),
    (re.compile(r'\bdata-target='), 'data-bs-target='),
]


class Command(BaseCommand):
    help = 'Reemplaza atributos Bootstrap 4 (data-toggle/data-target) por sus equivalentes Bootstrap 5 en Pagina.contenido.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Aplica los cambios y guarda. Sin esta flag corre en modo dry-run.',
        )
        parser.add_argument(
            '--slug', default=None,
            help='Restringe a una sola pagina por slug. Util para probar antes de correr global.',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        slug = options['slug']

        qs = Pagina.objects.all()
        if slug:
            qs = qs.filter(slug=slug)

        total_paginas = 0
        total_reemplazos = 0
        cambios_por_patron = {pat.pattern: 0 for pat, _ in REPLACEMENTS}

        with transaction.atomic():
            for pagina in qs.iterator():
                original = pagina.contenido or ''
                if not original:
                    continue

                nuevo = original
                cambios_pagina = 0
                for pat, repl in REPLACEMENTS:
                    nuevo_iter, n = pat.subn(repl, nuevo)
                    if n:
                        cambios_por_patron[pat.pattern] += n
                        cambios_pagina += n
                        nuevo = nuevo_iter

                if cambios_pagina == 0:
                    continue

                total_paginas += 1
                total_reemplazos += cambios_pagina

                self.stdout.write(
                    f'  {pagina.slug:60s}  {cambios_pagina:4d} reemplazos'
                )

                if apply:
                    pagina.contenido = nuevo
                    pagina.save(update_fields=['contenido'])

            if not apply:
                # Aborta la transaccion para que no se persista nada.
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\n{"APLICADO" if apply else "DRY-RUN"}: '
            f'{total_paginas} paginas, {total_reemplazos} reemplazos totales.'
        ))
        for patron, n in cambios_por_patron.items():
            self.stdout.write(f'  {patron}: {n}')

        if not apply:
            self.stdout.write(self.style.WARNING(
                '\nSin cambios persistidos. Ejecuta con --apply para guardar.'
            ))
