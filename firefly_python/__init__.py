from __future__ import absolute_import, unicode_literals

# This will ensure the Celery app is always imported when
# Django starts, avoiding the "no attribute 'celery'" error.
from .celery import app as celery_app

__all__ = ('celery_app',)
