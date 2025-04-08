from django.db import models


class Article(models.Model):
    board = models.ForeignKey('Board', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    author = models.ForeignKey('Author', on_delete=models.CASCADE)
    content = models.TextField()
    time = models.DateTimeField()
    url = models.URLField(max_length=255)

    def __str__(self):
        return self.url


class Board(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name