from celery import Celery

from config import settings
from tasks.schedule import beat_schedule

celery_app = Celery(
    "checkers",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "tasks.payments",
    ],
)

celery_app.conf.update(
    timezone="Asia/Almaty",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    beat_schedule=beat_schedule,
)
