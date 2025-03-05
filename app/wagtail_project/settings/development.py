from .base import *

DEBUG = os.getenv('DEBUG', 'False') == 'True'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-for-development-only')

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CSRF settings
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = ['http://localhost:8001', 'http://127.0.0.1:8001']
CSRF_USE_SESSIONS = True

# Session settings
SESSION_COOKIE_SECURE = False

# Static files settings
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Add whitenoise for serving static files in development
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

try:
    from .local import *
except ImportError:
    pass
