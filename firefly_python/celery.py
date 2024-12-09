from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set the default Django settings module for the Celery program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'firefly_python.settings')

# Create the Celery app
app = Celery('firefly_python')

# Load settings from the Django settings file
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
