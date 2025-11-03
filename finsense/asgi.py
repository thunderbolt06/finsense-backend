"""ASGI config for finsense project."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finsense.settings")

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

