
"""Celery app configuration."""

import os
from celery import Celery
from kombu import Queue, Exchange

# Create celery app
app = Celery('automagik')

# Configure celery
app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('high_priority', Exchange('high_priority'), routing_key='high_priority'),
        Queue('low_priority', Exchange('low_priority'), routing_key='low_priority'),
    ),
    task_default_queue='default',
    task_routes={
        'automagik.core.tasks.workflow_tasks.execute_workflow': {'queue': 'default'},
    },
    worker_concurrency=int(os.getenv('CELERY_WORKER_CONCURRENCY', 2)),
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_retry_max_retries=3,
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes max backoff
    beat_schedule={},  # Will be populated dynamically
    beat_max_loop_interval=60,  # Check for new schedules every minute
    beat_scheduler='automagik.core.celery_config.DatabaseScheduler',
    beat_schedule_filename=os.path.expanduser('~/.automagik/celerybeat-schedule'),
    imports=(
        'automagik.core.tasks.workflow_tasks',
    ),
    worker_prefetch_multiplier=1,  # Disable prefetching
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    worker_max_memory_per_child=200000,  # 200MB memory limit
    task_time_limit=3600,  # 1 hour timeout
    task_soft_time_limit=3300,  # 55 minutes soft timeout
    broker_connection_retry_on_startup=True,
    broker_pool_limit=None,  # Disable connection pooling
    broker_connection_max_retries=None,  # Retry forever
    broker_connection_retry=True,
    broker_heartbeat=10,
    event_queue_expires=60,
    worker_lost_wait=10,
    worker_disable_rate_limits=True,
)

# Load tasks module
app.autodiscover_tasks(['automagik.core.tasks'])


