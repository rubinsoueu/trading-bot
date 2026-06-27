import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:***@app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=280,
)
