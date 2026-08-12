import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


DEBUG = env_bool('AHHH_DEBUG', False)

# True durante la suite de tests (manage.py test fuerza DEBUG=False).
TESTING = 'test' in sys.argv

SECRET_KEY = os.getenv('AHHH_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('AHHH_SECRET_KEY es obligatoria cuando AHHH_DEBUG=False.')
    SECRET_KEY = 'django-insecure-local-development-only'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        'AHHH_ALLOWED_HOSTS',
        'localhost,127.0.0.1,[::1],100.95.61.46',
    ).split(',')
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('AHHH_CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Apps
    'apps.accounts',
    'apps.ads',
    'apps.payments.apps.PaymentsConfig',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', # Activated
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.accounts.context_processors.site_configuration',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('AHHH_POSTGRES_DB', 'ahhh_db'),
        'USER': os.getenv('AHHH_POSTGRES_USER', 'ahhh_user'),
        'PASSWORD': os.getenv('AHHH_POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('AHHH_DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('AHHH_DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Rate limiting para login y registros (formato django-ratelimit: "5/h", "10/5m", ...)
AHHH_AUTH_RATE = os.getenv('AHHH_AUTH_RATE', '5/h')

# Pasarela de pagos activa ('dummy' en desarrollo). Ver apps/payments/gateways/.
AHHH_PAYMENT_GATEWAY = os.getenv('AHHH_PAYMENT_GATEWAY', 'dummy')

# Cache: locmem por defecto (dev). En produccion usar Redis para que el rate
# limiting sea compartido entre todos los workers de gunicorn.
if os.getenv('AHHH_REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('AHHH_REDIS_URL'),
        },
    }

# Internationalization
LANGUAGE_CODE = 'es'

TIME_ZONE = os.getenv('AHHH_TIME_ZONE', 'Europe/Madrid')

USE_I18N = True

USE_L10N = True

USE_TZ = True

# LANGUAGES CONFIGURATION
LANGUAGES = [
    ('es', _('Spanish')),
    ('en', _('English')),
    ('ru', _('Russian')),
    ('ar', _('Arabic')),
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Storage por defecto: local. En produccion nginx sirve /static/ y /media/.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool('AHHH_SECURE_SSL_REDIRECT', True)
    SECURE_HSTS_SECONDS = int(os.getenv('AHHH_SECURE_HSTS_SECONDS', '3600'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Redirects
LOGIN_REDIRECT_URL = 'user_dispatch'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'login'
