"""
Dert Ortağı — Django ayarları.

Tüm gizli ve ortama bağlı değerler ortam değişkenlerinden (veya .env
dosyasından) okunur. Kod deposunda hiçbir gizli anahtar bulunmaz.
"""

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent

# .env dosyası varsa yükle (python-dotenv opsiyoneldir)
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "evet"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Temel ayarlar
# --------------------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", False)
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY.startswith("degistir"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY tanımlı değil. .env.example dosyasını .env olarak "
        "kopyala ve README'deki komutla yeni bir anahtar üret."
    )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

# Yönetim paneli tahmin edilebilir /admin/ adresinde durmaz.
ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "yonetim/").strip("/") + "/"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Proje uygulamaları
    "core",
    "accounts",
    "dertler",
    "sohbet",
    "guvenlik",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.PrivacyHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.csp",
                "core.context_processors.site",
            ],
        },
    },
]

# --------------------------------------------------------------------------
# Veritabanı: varsayılan SQLite (geliştirme), istenirse PostgreSQL
# --------------------------------------------------------------------------
if os.environ.get("DB_ENGINE", "sqlite").lower() == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "dert_ortagi"),
            "USER": os.environ.get("POSTGRES_USER", ""),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

# --------------------------------------------------------------------------
# Kimlik doğrulama ve parolalar
# --------------------------------------------------------------------------
# scrypt bellek-yoğun bir algoritmadır ve ek bağımlılık gerektirmez.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
if TESTING:
    # Testleri hızlandırmak için; yalnızca test komutunda geçerli.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dertler:list"
LOGOUT_REDIRECT_URL = "core:home"

# --------------------------------------------------------------------------
# Oturum, çerez ve HTTP güvenlik başlıkları
# --------------------------------------------------------------------------
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 gün
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Üçüncü taraf hiçbir kaynak yüklenmez: yazı tipi dahil her şey bu sunucudan.
# Bu sayede ziyaretçi verisi yurt dışına aktarılmaz (KVKK m.9).
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:"],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "object-src": [CSP.NONE],
}

if not DEBUG and not TESTING:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 60 * 60 * 24 * 365)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)
    if env_bool("DJANGO_BEHIND_PROXY", False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Dosya yükleme özelliği yok; istek boyutlarını düşük tut.
DATA_UPLOAD_MAX_MEMORY_SIZE = 512 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200
FILE_UPLOAD_MAX_MEMORY_SIZE = 0

# --------------------------------------------------------------------------
# Önbellek (hız sınırlama için kullanılır)
# Birden fazla süreçte çalışırken Redis gibi paylaşımlı bir önbellek kullan.
# --------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "dert-ortagi",
    }
}

# --------------------------------------------------------------------------
# E-posta (parola sıfırlama). Geliştirmede konsola yazar.
# --------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", "noreply@localhost")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
PASSWORD_RESET_TIMEOUT = 60 * 60  # 1 saat

# --------------------------------------------------------------------------
# Dil, saat dilimi, statik dosyalar
# --------------------------------------------------------------------------
LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or TESTING
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# --------------------------------------------------------------------------
# Günlükleme: mesaj veya dert içerikleri asla günlüğe yazılmaz.
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "dertortagi": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

if TESTING:
    LOGGING["loggers"]["django.request"] = {"handlers": ["console"], "level": "ERROR", "propagate": False}

# --------------------------------------------------------------------------
# Uygulamaya özel ayarlar
# --------------------------------------------------------------------------
# Yasal metinlerin sürümleri. Metin değişince sürümü artır; kullanıcılar
# hangi sürümü kabul ettiklerini ConsentRecord tablosunda görür.
LEGAL_VERSIONS = {
    "terms": "1.0",
    "privacy": "1.0",
    "special_data": "1.0",
}

# Bu kadar farklı kullanıcı şikayet ederse dert, moderatör bakana kadar gizlenir.
AUTO_HIDE_REPORT_THRESHOLD = env_int("AUTO_HIDE_REPORT_THRESHOLD", 3)

# Saklama ve imha süreleri (gün) — `python manage.py kvkk_temizlik`
RETENTION_DAYS = {
    "closed_conversations": env_int("RETENTION_CLOSED_CONVERSATIONS", 90),
    "resolved_reports": env_int("RETENTION_RESOLVED_REPORTS", 365),
    "hidden_dertler": env_int("RETENTION_HIDDEN_DERTLER", 180),
    "inactive_accounts": env_int("RETENTION_INACTIVE_ACCOUNTS", 730),
}

# Veri sorumlusu bilgileri (canlıya alınırsa doldurulmalı)
DATA_CONTROLLER = {
    "name": os.environ.get("DATA_CONTROLLER_NAME", "[Veri sorumlusunun adı / unvanı]"),
    "address": os.environ.get("DATA_CONTROLLER_ADDRESS", "[Adres]"),
    "contact": os.environ.get("DATA_CONTROLLER_CONTACT", "[KVKK başvuru e-posta adresi]"),
}
