from pinecone import Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from env_settings import settings
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from ptt_rag.celery import app
from article_app.models import Article


@app.task()
def store_data_in_pinecone(article_id_list: list):
    vector_store = PineconeVectorStore(
        index=Pinecone(
            api_key=settings.pinecone_api_key
        ).Index(settings.pinecone_index_name),
        embedding=OpenAIEmbeddings(api_key=settings.openai_api_key)
    )
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=20,
        separators=["\n\n","\n---\n","\n--\n", "\n", "。", "！", "？", "，", " ", ""]
    )
    for article in Article.objects.filter(id__in=article_id_list).all():
        chunks = text_splitter.split_text(article.content)
        for i, chunk in enumerate(chunks):
            documents.append(Document(
                page_content=chunk,
                metadata={
                    "article_id": article.id,
                    "board": article.board.name,
                    "title": article.title,
                    "author": article.author.name,
                    "post_time": str(article.post_time),
                    "url": article.url,
                    "chunk_index": i
                }
            ))
    vector_store.add_documents(documents=documents)

    # Test0
    vector_store = PineconeVectorStore(
        index=Pinecone(
            api_key=settings.pinecone_api_key
        ).Index('ptt100'),
        embedding=OpenAIEmbeddings(api_key=settings.openai_api_key)
    )
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=20,
        separators=["\n\n", "\n---\n", "\n--\n", "\n", "。", "！", "？", "，", " ", ""]
    )
    for article in Article.objects.filter(id__in=article_id_list).all():
        chunks = text_splitter.split_text(article.content)
        for i, chunk in enumerate(chunks):
            documents.append(Document(
                page_content=chunk,
                metadata={
                    "article_id": article.id,
                    "board": article.board.name,
                    "title": article.title,
                    "author": article.author.name,
                    "post_time": str(article.post_time),
                    "url": article.url,
                    "chunk_index": i
                }
            ))
    vector_store.add_documents(documents=documents)

    # Test1
    vector_store = PineconeVectorStore(
        index=Pinecone(
            api_key=settings.pinecone_api_key
        ).Index('ptt300'),
        embedding=OpenAIEmbeddings(api_key=settings.openai_api_key)
    )
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=60,
        separators=["\n\n", "\n---\n", "\n--\n", "\n", "。", "！", "？", "，", " ", ""]
    )
    for article in Article.objects.filter(id__in=article_id_list).all():
        chunks = text_splitter.split_text(article.content)
        for i, chunk in enumerate(chunks):
            documents.append(Document(
                page_content=chunk,
                metadata={
                    "article_id": article.id,
                    "board": article.board.name,
                    "title": article.title,
                    "author": article.author.name,
                    "post_time": str(article.post_time),
                    "url": article.url,
                    "chunk_index": i
                }
            ))
    vector_store.add_documents(documents=documents)

    # Test2
    vector_store = PineconeVectorStore(
        index=Pinecone(
            api_key=settings.pinecone_api_key
        ).Index('ptt500'),
        embedding=OpenAIEmbeddings(api_key=settings.openai_api_key)
    )
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n---\n", "\n--\n", "\n", "。", "！", "？", "，", " ", ""]
    )
    for article in Article.objects.filter(id__in=article_id_list).all():
        chunks = text_splitter.split_text(article.content)
        for i, chunk in enumerate(chunks):
            documents.append(Document(
                page_content=chunk,
                metadata={
                    "article_id": article.id,
                    "board": article.board.name,
                    "title": article.title,
                    "author": article.author.name,
                    "post_time": str(article.post_time),
                    "url": article.url,
                    "chunk_index": i
                }
            ))
    vector_store.add_documents(documents=documents)