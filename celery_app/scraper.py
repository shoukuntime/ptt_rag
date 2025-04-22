import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ptt_rag.settings")
django.setup()

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from article_app.models import Article, Board, Author
from log_app.models import Log
from celery_app.data_processing import store_data_in_pinecone
from ptt_rag.celery import app
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from env_settings import settings
from zoneinfo import ZoneInfo
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from celery import chain
import traceback


@app.task()
def period_send_ptt_scrape_task():
    board_list = ['Gossiping', 'NBA', 'Stock', 'LoL', 'home-sale']
    for board in board_list:
        chain(ptt_scrape.s(board), store_data_in_pinecone.s())()


def get_html(url: str) -> str:
    session = requests.Session()
    payload = {
        "from": url,
        "yes": "yes"
    }
    session.post("https://www.ptt.cc/ask/over18", data=payload)
    response = session.get(url)
    return response.text


def get_urls_from_board_html(html: str, board: str) -> list:
    html_soup = BeautifulSoup(html, 'html.parser')
    r_ent_all = html_soup.find_all('div', class_='r-ent')
    urls = []
    for r_ent in r_ent_all:
        # 若無r_ent.find('a')['href']代表文章已刪除
        if r_ent.find('a'):
            if r_ent.find('a')['href']:
                urls.append('https://www.ptt.cc' + r_ent.find('a')['href'])
    return urls


def get_data_from_article_html(html: str, board: str) -> dict:
    html_soup = BeautifulSoup(html, 'html.parser')
    article_soup = html_soup.find('div', class_='bbs-screen bbs-content')
    title = article_soup.find_all('span', class_='article-meta-value')[2].text
    author = article_soup.find_all('span', class_='article-meta-value')[0].text.strip(')').split(' (')[0]
    time_str = article_soup.find_all('span', class_='article-meta-value')[3].text
    dt = datetime.strptime(time_str, "%a %b %d %H:%M:%S %Y")
    dt = dt.replace(tzinfo=ZoneInfo("Asia/Taipei"))
    post_time = dt.strftime("%Y-%m-%d %H:%M:%S")

    result = []
    for element in article_soup.children:
        if element.name not in ["div", "span"]:
            text = element.get_text(strip=True) if element.name == "a" else str(element).strip()
            if text:
                result.append(text)
    content = "\n".join(result).strip('-')

    data = {
        'board': board,
        'title': title,
        'author': author,
        'post_time': post_time,
        'content': content,
    }
    return data


def get_data_from_article_html_with_llm(html: str) -> dict:
    query = f"""
        以下是 HTML 內容，請幫我提取以下欄位：
        - 看板 (board)
        - 標題 (title)
        - 作者 (author)
        - 時間 (post_time)
        - 內容 (content)

        HTML 內容：
        ```
        {html}
        ```

        回傳格式為 JSON，例如：
        {{
            "board": "example_board",
            "title": "example_title",
            "author": "example_author",
            "post_time": "example_time",
            "content": "example_content"
        }}
        """
    model = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.openai_api_key)
    parser = JsonOutputParser()
    prompt = PromptTemplate(
        template="Answer the user query.\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain_result = prompt | model | parser
    data = chain_result.invoke({"query": query})
    data['author'] = data['author'].strip(')').split(' (')[0]
    return data


@app.task()
def ptt_scrape(board: str) -> list:
    Log.objects.create(level='INFO', type=f'scrape-{board}', message=f'開始爬取 {board}')
    board_url = 'https://www.ptt.cc/bbs/' + board + '/index.html'
    board_html = get_html(board_url)
    article_urls = get_urls_from_board_html(board_html, board)
    article_id_list = []
    for article_url in article_urls:
        if Article.objects.filter(url=article_url).exists():
            continue
        article_html = get_html(article_url)
        try:
            article_data = get_data_from_article_html(article_html, board)
        except Exception as e:
            Log.objects.create(level='ERROR', type=f'scrape-{board}', message=f'從url:{article_url}取得data失敗，使用LLM處理: {e}',
                               traceback=traceback.format_exc())
            article_data = None
        if not article_data:
            try:
                article_data = get_data_from_article_html_with_llm(article_html)
            except Exception as e:
                Log.objects.create(level='ERROR', type=f'scrape-{board}', message=f'{article_url}LLM處理失敗: {e}',
                                   traceback=traceback.format_exc())
                continue
        try:
            board_obj, _ = Board.objects.get_or_create(name=article_data['board'])
            author_obj, _ = Author.objects.get_or_create(name=article_data['author'])
            if len(article_data['content'])<=30000:
                article = Article.objects.create(
                    board=board_obj,
                    title=article_data['title'],
                    author=author_obj,
                    content=article_data['content'],
                    post_time=article_data['post_time'],
                    url=article_url
                )
            else:
                Log.objects.create(level='INFO', type=f'scrape-{board}',
                                   message=f'文章內容過長,url:{article_url}')
                continue
            article_id_list.append(article.id)
        except Exception as e:
            Log.objects.create(level='ERROR', type=f'scrape-{board}', message=f'{article_url}Data插入資料庫錯誤: {e}',
                               traceback=traceback.format_exc())
    Log.objects.create(level='INFO', type=f'scrape-{board}', message=f'爬取 {board} 完成')
    return article_id_list