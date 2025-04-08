from django.db import models

from article_app.models import Board


class Log(models.Model):
    level = models.CharField(max_length=100)
    step = models.CharField(max_length=100)
    message = models.TextField()
    traceback = models.TextField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.level} - {self.created_at}'
