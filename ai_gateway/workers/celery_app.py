"""
Celery Campaign Workers — standard priority queue execution.
Patent-safe: Uses static queue priorities, NOT ML-predicted resource allocation
(which is patented by Adobe in US11025713B2).
"""
from celery import Celery
from celery.schedules import crontab
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "openengage",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["workers.tasks"]
)

celery_app.conf.update(
    task_routes={
        "workers.tasks.run_trigger_campaign": {"queue": "campaign"},
        "workers.tasks.run_batch_campaign":   {"queue": "campaign"},
        "workers.tasks.send_email":           {"queue": "email"},
        "workers.tasks.update_lead_scores":   {"queue": "scoring"},
        "workers.tasks.run_agent_task":       {"queue": "agents"},
    },
    beat_schedule={
        "sync-mautic-contacts": {
            "task": "workers.tasks.sync_mautic_contacts",
            "schedule": crontab(minute="*/5"),
        },
        "daily-score-recalculation": {
            "task": "workers.tasks.update_all_lead_scores",
            "schedule": crontab(hour=2, minute=0),
        },
        "weekly-campaign-suggestions": {
            "task": "workers.tasks.generate_campaign_suggestions",
            "schedule": crontab(day_of_week=1, hour=8),
        },
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
)
