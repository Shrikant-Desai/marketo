from celery import Celery
from config import get_settings

settings = get_settings()

celery_app = Celery(
    "marketo",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_expires=3600,
    timezone="UTC",
)

celery_app.autodiscover_tasks(["tasks"])
