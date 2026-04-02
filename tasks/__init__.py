# tasks/__init__.py
from .celery_app import celery_app
from .email_tasks import *

__all__ = ["celery_app"]
