from rest_framework import generics
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Article
from .serializers import ArticleSerializer
from rest_framework.pagination import LimitOffsetPagination
from django.shortcuts import render
from rest_framework import viewsets
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
import openai
from env_settings import settings
from rest_framework import status
from pinecone import Pinecone

class ArticleListView(generics.ListAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['author_id', 'kanban', 'time']
    pagination_class = LimitOffsetPagination

    @swagger_auto_schema(
        operation_description="取得最新 50 篇文章，可使用 limit、offset 進行分頁，並透過作者 ID、版面、時間進行過濾。",
        manual_parameters=[
            openapi.Parameter('limit', openapi.IN_QUERY, description="每頁返回的筆數 (預設 50)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('offset', openapi.IN_QUERY, description="從第幾筆開始 (預設 0)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('author_id', openapi.IN_QUERY, description="篩選特定發文者的文章", type=openapi.TYPE_INTEGER),
            openapi.Parameter('kanban', openapi.IN_QUERY, description="篩選特定版面的文章", type=openapi.TYPE_STRING),
            openapi.Parameter('time', openapi.IN_QUERY, description="篩選特定時間的文章 (Unix Timestamp，單位：秒)", type=openapi.TYPE_INTEGER),
        ],
        responses={200: ArticleSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        """取得最新 50 篇文章，支援分頁與過濾條件"""
        return super().get(request, *args, **kwargs)

class ArticleDetailView(generics.RetrieveAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    @swagger_auto_schema(
        operation_description="根據文章 ID 取得特定文章的詳細內容。",
        responses={200: ArticleSerializer()}
    )
    def get(self, request, *args, **kwargs):
        """取得單篇文章詳細資訊"""
        return super().get(request, *args, **kwargs)


class ArticleStatisticsView(APIView):
    @swagger_auto_schema(
        operation_description="取得文章統計資訊，支援時間範圍、作者 ID 和版面過濾",
        manual_parameters=[
            openapi.Parameter(
                'start_date', openapi.IN_QUERY, description="起始日期 (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE
            ),
            openapi.Parameter(
                'end_date', openapi.IN_QUERY, description="結束日期 (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE
            ),
            openapi.Parameter(
                'author_id', openapi.IN_QUERY, description="發文者 ID", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'kanban', openapi.IN_QUERY, description="版面名稱", type=openapi.TYPE_STRING
            ),
        ],
        responses={200: openapi.Response("文章統計結果", openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'total_posts': openapi.Schema(type=openapi.TYPE_INTEGER, description="文章總數"),
            }
        ))}
    )
    def get(self, request):
        posts = Article.objects.all()

        # 過濾時間範圍
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        parsed_start_date = parse_date(start_date) if start_date else None
        parsed_end_date = parse_date(end_date) if end_date else None

        if parsed_start_date and parsed_end_date:
            posts = posts.filter(time__range=[parsed_start_date, parsed_end_date])
        elif parsed_start_date:
            posts = posts.filter(time__gte=parsed_start_date)
        elif parsed_end_date:
            posts = posts.filter(time__lte=parsed_end_date)

        # 過濾作者
        author_id = request.query_params.get('author_id')
        if author_id:
            posts = posts.filter(author_id=author_id)

        # 過濾版面
        kanban = request.query_params.get('kanban')
        if kanban:
            posts = posts.filter(kanban=kanban)

        # 計算統計數據
        total_posts = posts.count()

        return Response({"total_posts": total_posts})


pc = Pinecone(api_key=settings.pinecone_api_key)
index = pc.Index(settings.pinecone_index_name)


class SearchAPIView(APIView):
    def post(self, request):
        query = request.data.get("query", "")

        if not query:
            return Response({"error": "Query cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
        response = openai.Embedding.create(
            input=query,
            model="text-embedding-ada-002"
        )
        query_embedding = response["data"][0]["embedding"]
        search_results = index.query(vector=query_embedding, top_k=5, include_metadata=True)

        related_articles = []
        for match in search_results["matches"]:
            url = match["url"]
            article = Article.objects.filter(url=url).first()
            if article:
                related_articles.append({
                    "id": article.id,
                    "title": article.title,
                    "url": article.url
                })

        context_text = "\n".join([f"{a['title']} - {a['url']}" for a in related_articles])
        prompt = f"根據以下文章內容回答問題：\n\n{context_text}\n\n問題：{query}\n回答："
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = response["choices"][0]["message"]["content"]

        return Response({
            "question": query,
            "related_articles": related_articles,
            "response": response_text
        }, status=status.HTTP_200_OK)
