import os
from pathlib import Path

import dj_database_url
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── SEGURIDAD ────────────────────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ─── APLICACIONES ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'crispy_forms',
    'crispy_bootstrap5',
    'django_ckeditor_5',

    # Local apps
    'apps.core',
    'apps.noticias',
    'apps.contacto',
    'apps.reclamos',
    'apps.tarjetas',
    'apps.biblioteca',
    'apps.concursos',
    'apps.boletines',
    'apps.menus',
    'apps.calendario',
    'apps.archivos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.menus.context_processors.menu_popup_context',
                'apps.core.context_processors.sidebar_legacy_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─── BASE DE DATOS ────────────────────────────────────────────────────────────
# Si DATABASE_URL está vacía o ausente en .env → SQLite en desarrollo.
# En producción: DATABASE_URL=mysql://user:pass@host:3306/dbname
#                DATABASE_URL=postgres://user:pass@host:5432/dbname
_db_url = config('DATABASE_URL', default='')
if _db_url:
    DATABASES = {
        'default': dj_database_url.parse(
            _db_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Desarrollo local: SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ─── VALIDACIONES DE CONTRASEÑA ───────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── INTERNACIONALIZACIÓN ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-py'
TIME_ZONE = 'America/Asuncion'
USE_I18N = True
USE_TZ = True

# ─── ARCHIVOS ESTÁTICOS Y MEDIA ───────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── CRISPY FORMS ─────────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ─── EMAIL ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@dinapi.gov.py')


# ─── CKEDITOR 5 ──────────────────────────────────────────────────────────────
# Editor WYSIWYG para campos HTML del admin. Dos perfiles:
#   - 'extended': para contenido HTML rico (Pagina, Noticia, AcordeonItem, etc.)
#                 con tablas, imágenes y soporte completo de HTML legacy
#                 (data-bs-toggle, clases custom, atributos data-*).
#   - 'basic':    para descripciones cortas (categorías, etiquetas, etc.)
CKEDITOR_5_ALLOW_ALL_FILE_TYPES = False
CKEDITOR_5_UPLOAD_FILE_TYPES = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']

# Permitir TODO el HTML legacy sin sanitizar (data-*, classes, styles).
# Imprescindible para preservar acordeones Bootstrap 5 migrados.
_CKE_FULL_HTML_SUPPORT = {
    'allow': [
        {
            'name': '/.*/',
            'attributes': True,
            'classes': True,
            'styles': True,
        }
    ]
}

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': [
            'heading', '|',
            'bold', 'italic', 'underline', 'link', '|',
            'bulletedList', 'numberedList', '|',
            'blockQuote', '|',
            'removeFormat', 'undo', 'redo',
        ],
        'language': 'es',
    },
    'basic': {
        'toolbar': [
            'bold', 'italic', 'link', '|',
            'bulletedList', 'numberedList', '|',
            'removeFormat', 'undo', 'redo',
        ],
        'language': 'es',
    },
    'extended': {
        'toolbar': [
            'heading', '|',
            'bold', 'italic', 'underline', 'strikethrough', 'link', '|',
            'bulletedList', 'numberedList', 'outdent', 'indent', '|',
            'imageUpload', 'mediaEmbed', 'insertTable', 'blockQuote', '|',
            'horizontalLine', 'specialCharacters', 'removeFormat', '|',
            'sourceEditing', 'undo', 'redo',
        ],
        'language': 'es',
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter',
                        'imageStyle:side', '|'],
            'styles': ['full', 'side', 'alignLeft', 'alignRight', 'alignCenter'],
        },
        'table': {
            'contentToolbar': ['tableColumn', 'tableRow', 'mergeTableCells',
                               'tableProperties', 'tableCellProperties'],
        },
        'heading': {
            'options': [
                {'model': 'paragraph', 'title': 'Parrafo', 'class': 'ck-heading_paragraph'},
                {'model': 'heading2', 'view': 'h2', 'title': 'Titulo 2', 'class': 'ck-heading_heading2'},
                {'model': 'heading3', 'view': 'h3', 'title': 'Titulo 3', 'class': 'ck-heading_heading3'},
                {'model': 'heading4', 'view': 'h4', 'title': 'Titulo 4', 'class': 'ck-heading_heading4'},
            ]
        },
        # CRITICO: preserva todo el HTML legacy (acordeones BS5, data-*, clases).
        'htmlSupport': _CKE_FULL_HTML_SUPPORT,
    },
}

# Subida de archivos del editor: usa el storage por default (media/).
