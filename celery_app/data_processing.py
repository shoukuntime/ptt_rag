from pinecone import Pinecone, ServerlessSpec
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Pinecone as LangChainPinecone
from langchain_openai import OpenAIEmbeddings
from env_settings import settings


def connect_to_pinecone() -> (Pinecone, LangChainPinecone):
    """
    連接 Pinecone
    :return: Pinecone 連接和 OpenAI 向量嵌入
    """
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(settings.pinecone_index_name)
    embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)
    return index, embeddings


def store_data_in_pinecone(data: dict, index, embeddings: OpenAIEmbeddings):
    """
    將文字存入 Pinecone
    :param data
    :param index: Pinecone 索引
    :param embeddings: 文字向量
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
    chunks = text_splitter.split_text(data['content'])
    docs = [{"id": f"{data['url']}_{i}", "values": embeddings.embed_query(chunk),
             "metadata": {"text": chunk, "kanban": data['kanban'], "title": data['title'],
                          "author": data['author'], "time": data['time'], "url": data['url']}}
            for i, chunk in enumerate(chunks)]
    index.upsert(vectors=docs)
