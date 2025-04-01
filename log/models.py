from django.db import models


class Log(models.Model):
    level = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField()

    def __str__(self):
        return f'{self.level} - {self.created_at}'
