from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from article_app.models import Article,Board,Author
from django.urls import reverse
from django.utils import timezone


class ArticleAPITests(APITestCase):
    def setUp(self):
        board_obj, _ = Board.objects.get_or_create(name='test_board')
        author_obj, _ = Author.objects.get_or_create(name='test_author')
        self.article = Article.objects.create(
            board=board_obj,
            title='test_title',
            author=author_obj,
            content="test_content",
            post_time=timezone.now(),
            url="test_url",
        )

    def test_get_article_list(self):
        url = reverse('article-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(len(response.data), 1)
        # self.assertEqual(response.data[0]['title'], "test_title")