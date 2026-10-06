"""SIGPI Django project package.

Expose the Celery app so ``celery -A config`` resolves it and shared tasks
bind to the same app the Django process loads.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
