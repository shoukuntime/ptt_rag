from datetime import datetime, time
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, inline_serializer
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from .models import Article
from .serializers import ArticleSerializer, QueryRequestSerializer, ArticleListRequestSerializer
from env_settings import settings
from pinecone import Pinecone
from rest_framework.pagination import LimitOffsetPagination
import traceback
from log_app.models import Log
from langchain_pinecone import PineconeVectorStore


def articles_filter(article_list_request_serializer):
    articles=Article.objects.all()
    author_name=article_list_request_serializer.validated_data.get("author_name")
    board_name=article_list_request_serializer.validated_data.get("board_name")
    start_date=article_list_request_serializer.validated_data.get("start_date")
    end_date=article_list_request_serializer.validated_data.get("end_date")
    if author_name:
        articles = articles.filter(author__name=author_name)
    if board_name:
        articles = articles.filter(board__name=board_name)
    start_datetime = datetime.combine(start_date, time.min) if start_date else None
    end_datetime = datetime.combine(end_date, time.max) if end_date else None
    if start_datetime and end_datetime:
        articles = articles.filter(post_time__range=[start_datetime, end_datetime])
    elif start_datetime:
        articles = articles.filter(post_time__gte=start_datetime)
    elif end_datetime:
        articles = articles.filter(post_time__lte=end_datetime)
    return articles


class ArticleListView(APIView):
    @extend_schema(
        description="取得最新 50 篇文章，可使用 limit、offset 進行分頁，可使用作者名稱、版面、時間範圍進行過濾。",
        parameters=[
            OpenApiParameter("limit", int, OpenApiParameter.QUERY, description="每頁返回的筆數 (預設 50)"),
            OpenApiParameter("offset", int, OpenApiParameter.QUERY, description="從第幾筆開始 (預設 0)"),
            OpenApiParameter("author_name", str, OpenApiParameter.QUERY, description="篩選特定發文者的文章"),
            OpenApiParameter("board_name", str, OpenApiParameter.QUERY, description="篩選特定版面的文章"),
            OpenApiParameter("start_date", str, OpenApiParameter.QUERY, description="篩選起始日期 (YYYY-MM-DD)", ),
            OpenApiParameter("end_date", str, OpenApiParameter.QUERY, description="篩選結束日期 (YYYY-MM-DD)", ),
        ],
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name='ArticleListResponse',
                    fields={
                        'count': serializers.IntegerField(read_only=True),
                        'next': serializers.CharField(read_only=True),
                        'previous': serializers.CharField(read_only=True),
                        'results': ArticleSerializer(many=True, read_only=True),
                    }
                ),
            )
        },
    )
    def get(self, request):
        article_list_request_serializer = ArticleListRequestSerializer(data=request.query_params)
        if not article_list_request_serializer.is_valid():
            Log.objects.create(level='ERROR', type='user-posts', message='查詢參數不合法',
                               traceback=traceback.format_exc())
            return Response(article_list_request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        articles = articles_filter(article_list_request_serializer)
        paginator = LimitOffsetPagination()
        paginator.default_limit = 50
        paginated_queryset = paginator.paginate_queryset(articles.order_by('id'), request)
        serializer = ArticleSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class ArticleDetailView(APIView):
    @extend_schema(
        description="根據文章 ID 取得特定文章的詳細內容。",
        responses={200: ArticleSerializer(),
                   404: OpenApiResponse(response={"type": "object", "properties": {"error": {"type": "string"}}})}
    )
    def get(self, request, pk):
        if pk<=0:
            Log.objects.create(level='ERROR', type='user-posts_id', message='文章ID須為正數',)
            return Response({"error": "文章ID須為正數"}, status=status.HTTP_404_NOT_FOUND)
        try:
            articles = Article.objects.get(id=pk)
        except Article.DoesNotExist:
            Log.objects.create(level='ERROR', type='user-posts_id', message='找不到文章，請輸入正確文章ID',
                               traceback=traceback.format_exc())
            return Response({"error": "找不到文章，請輸入正確文章ID"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ArticleSerializer(articles).data, status=status.HTTP_200_OK)


class ArticleStatisticsView(APIView):
    @extend_schema(
        description="取得文章統計資訊，支援時間範圍、作者名稱和版面過濾",
        parameters=[
            OpenApiParameter("author_name", str, OpenApiParameter.QUERY, description="篩選特定發文者的文章"),
            OpenApiParameter("board_name", str, OpenApiParameter.QUERY, description="篩選特定版面的文章"),
            OpenApiParameter("start_date", str, OpenApiParameter.QUERY, description="篩選起始日期 (YYYY-MM-DD)", ),
            OpenApiParameter("end_date", str, OpenApiParameter.QUERY, description="篩選結束日期 (YYYY-MM-DD)", ),
        ],
        responses={
            200: OpenApiResponse(response={"type": "object", "properties": {"total_articles": {"type": "integer"}}}),
            400: OpenApiResponse(response={"type": "object", "properties": {"error": {"type": "string"}}}),
        }
    )
    def get(self, request):
        article_list_request_serializer = ArticleListRequestSerializer(data=request.query_params)
        if not article_list_request_serializer.is_valid():
            Log.objects.create(level='ERROR', type='user-posts', message='查詢參數不合法',)
            return Response(article_list_request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        articles = articles_filter(article_list_request_serializer)
        total_articles = articles.count()
        return Response({"total_articles": total_articles})


class SearchAPIView(APIView):
    @extend_schema(
        methods=("POST",),
        description="輸入question(問題)與top_k(想查詢的文章片段數)，藉由LLM與向量資料庫得到question、answer(相關回答)、related_articles(相關文章)。",
        request=QueryRequestSerializer,
        responses=QueryRequestSerializer
    )
    def post(self, request):
        query_request_serializer = QueryRequestSerializer(data=request.data)
        if not query_request_serializer.is_valid():
            Log.objects.create(level='ERROR', type='user-search', message='查詢參數不合法',)
            return Response(query_request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        question = query_request_serializer.validated_data.get("question")
        top_k = query_request_serializer.validated_data.get("top_k")
        # 查詢Pinecone embeddings內容
        try:
            vector_store = PineconeVectorStore(
                index=Pinecone(
                    api_key=settings.pinecone_api_key
                ).Index('ptt'),
                embedding=OpenAIEmbeddings(api_key=settings.openai_api_key)
            )
            top_k_results = vector_store.similarity_search_with_score(question, k=top_k, )
        except Exception as e:
            Log.objects.create(level='ERROR', type='user-search', message=f'查詢Pinecone embeddings內容發生錯誤: {e}',
                               traceback=traceback.format_exc())
            return Response({"error": f"查詢Pinecone embeddings內容發生錯誤: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # # Test
        # test_ids = [match[0].id for match in top_k_results]
        # test_score=[match[1] for match in top_k_results]
        # return Response({"test_ids": test_ids,'test_score':test_score})
        # # ---
        # 從資料庫找出文章內容並合併
        try:
            match_ids = [match[0].metadata['article_id'] for match in top_k_results]
            query_request_serializer.related_articles = Article.objects.filter(id__in=match_ids)
            context_text = "\n".join(
                [f"Title:{a.title} - Content:{a.content}" for a in query_request_serializer.related_articles])
            if len(context_text)>128000:
                Log.objects.create(level='ERROR', type='user-search', message='回傳文章總字數過長，請嘗試減少top_k')
                return Response(
                    {"error": "回傳文章總字數過長，請嘗試減少top_k"},
                    status=status.HTTP_400_BAD_REQUEST)
        except (KeyError, TypeError) as e:
            Log.objects.create(level='ERROR', type='user-search', message=f'從資料庫找出文章內容發生錯誤: {e}',
                               traceback=traceback.format_exc())
            return Response(
                {"error": f"從資料庫找出文章內容發生錯誤: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # 請求 ChatGPT 回答問題
        try:
            model = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.openai_api_key)
            ptt_template = PromptTemplate(
                input_variables=["context_text", "question"],
                template="""
                根據以下PTT的文章內容回答問題：{context_text}
                問題：{question}
                回答：回傳格式為純文字，例如：
                "根據最近 PTT 討論，..."
                """
            )
            chain = ptt_template| model
            answer = chain.invoke({"context_text": context_text, "question": question}).content
        except Exception as e:
            Log.objects.create(level='ERROR', type='user-search', message=f'請求ChatGPT回答發生錯誤: {e}',
                               traceback=traceback.format_exc())
            return Response({"error": f"請求ChatGPT回答問題發生錯誤: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            serializer = QueryRequestSerializer(instance={
                "question": question,
                "answer": answer,
                "related_articles": Article.objects.filter(id__in=match_ids),
            })
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            Log.objects.create(level='ERROR', type='user-search', message=f'序列化輸出資料失敗: {e}',
                               traceback=traceback.format_exc())
            return Response({'error': '序列化輸出資料失敗'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
