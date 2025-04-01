from __future__ import absolute_import, unicode_literals
from celery import Celery
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptt_rag.settings')
django.setup()

app = Celery("ptt_rag", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0")
app.autodiscover_tasks()

app.conf.imports = [
    "celery_app.data_processing",
    "celery_app.scraper",
]

app.conf.beat_schedule = {
    'scrape-every-hour': {
        'task': 'celery_app.scraper.period_send_ptt_scrape_task',
        'schedule': 60,
    }
}

