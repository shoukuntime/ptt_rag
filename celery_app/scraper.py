import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ptt_rag.settings")
django.setup()

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from article.models import Article, Kanban, Author
from log.models import Log
from celery_app.data_processing import store_data_in_pinecone
from ptt_rag.celery import app
from django.utils import timezone
from langchain_openai import ChatOpenAI
from langchain.chains import create_retrieval_chain
from env_settings import settings
from zoneinfo import ZoneInfo
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from celery import group, chain, chord


@app.task()
def period_send_ptt_scrape_task():
    insert_log_into_db({'level': 'INFO', 'message': f'每小時爬蟲開始', 'created_at': str(datetime.now())})
    kanban_list = ['Gossiping', 'car', 'Stock', 'LoL', 'home-sale']
    for kanban in kanban_list:
        chain(ptt_scrape.s(kanban), store_data_in_pinecone.s())()
    insert_log_into_db({'level': 'INFO', 'message': f'每小時爬蟲結束', 'created_at': str(datetime.now())})


def get_html(url: str):
    """
    通過 URL 獲取 BeautifulSoup 物件
    :param url: 網址
    :return: html 物件
    """
    try:
        session = requests.Session()
        payload = {
            "from": url,
            "yes": "yes"
        }
        session.post("https://www.ptt.cc/ask/over18", data=payload)
        response = session.get(url)
        html = BeautifulSoup(response.text, "html.parser")
        return html
    except Exception as e:
        insert_log_into_db(
            {'level': 'ERROR', 'message': f'獲取 {url} 時發生錯誤 {e}', 'created_at': str(datetime.now())})


def get_urls_from_html_of_kanban(html: BeautifulSoup) -> list:
    """
    從 PTT 看版主頁的 BeautifulSoup 物件中取得看板的頁數和所有文章的網址
    :param soup: PTT 看版主頁的 BeautifulSoup 物件
    :return list: 網址列表
    """
    try:
        r_ent_all = html.find_all('div', class_='r-ent')
        urls = []
        for r_ent in r_ent_all:
            if r_ent.find('a')['href']:
                url_of_article = 'https://www.ptt.cc' + r_ent.find('a')['href']
                urls.extend([url_of_article])
            else:
                insert_log_into_db(
                    {'level': 'ERROR', 'message': f'獲取文章網址時發生錯誤', 'created_at': str(datetime.now())})
        return urls
    except Exception as e:
        insert_log_into_db(
            {'level': 'ERROR', 'message': f'獲取看板頁數和網址時發生錯誤 {e}', 'created_at': str(datetime.now())})
        return []


def get_data_from_url(url: str) -> dict:
    """
    從文章網址取得文章資訊
    :param url: 文章網址
    :return: 文章資訊字典
    """
    soup = get_html(url)
    kanban = url.split('/')[4]
    article = soup.find('div', class_='bbs-screen bbs-content')
    title = article.find_all('span', class_='article-meta-value')[2].text
    author = article.find_all('span', class_='article-meta-value')[0].text.strip(')').split(' (')[0]
    time_str = article.find_all('span', class_='article-meta-value')[3].text
    dt = datetime.strptime(time_str, "%a %b %d %H:%M:%S %Y")
    dt = dt.replace(tzinfo=ZoneInfo("Asia/Taipei"))
    time = dt.strftime("%Y-%m-%d %H:%M:%S")

    result = []
    for element in article.children:
        if element.name not in ["div", "span"]:
            text = element.get_text(strip=True) if element.name == "a" else str(element).strip()
            if text:
                result.append(text)
    content = "\n".join(result)

    data = {
        'kanban': kanban,
        'title': title,
        'author': author,
        'time': time,
        'content': content,
        'url': url
    }
    return data


def get_data_from_url_with_llm(url: str) -> dict:
    soup = get_html(url)
    html_str = str(soup)
    query = f"""
        以下是 HTML 內容，請幫我提取以下欄位：
        - 看板 (kanban)
        - 標題 (title)
        - 作者 (author)
        - 時間 (time)
        - 內容 (content)

        HTML 內容：
        ```
        {html_str}
        ```

        回傳格式為 JSON，例如：
        {{
            "kanban": "example_kanban",
            "title": "example_title",
            "author": "example_author",
            "time": "example_time",
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
    chain = prompt | model | parser
    data = chain.invoke({"query": query})
    data['author'] = data['author'].strip(')').split(' (')[0]
    data['url'] = url
    return data


def insert_log_into_db(log: dict):
    """
    將日誌插入MariaDB(資料庫)
    :param log: 日誌字典
    """
    print(log['message'])
    try:
        Log.objects.create(
            level=log['level'],
            message=log['message'],
            created_at=timezone.now()
        )
    except Exception as e:
        insert_log_into_db({'level': 'ERROR', 'message': f'Log插入資料庫錯誤: {e}', 'created_at': str(datetime.now())})


@app.task()
def ptt_scrape(kanban: str) -> list:
    """
    爬取看板最新的文章並存入MariaDB(資料庫)和 Pinecone(向量資料庫)
    :param kanban: 看板名稱
    :return article_id_list: 文章id列表
    """
    insert_log_into_db({'level': 'INFO', 'message': f'開始爬取 {kanban}', 'created_at': str(datetime.now())})
    kanban_url = 'https://www.ptt.cc/bbs/' + kanban + '/index.html'
    html = get_html(kanban_url)
    urls = get_urls_from_html_of_kanban(html)
    article_id_list = []
    for url in urls:
        try:
            data = get_data_from_url(url)
        except Exception as e:
            insert_log_into_db(
                {'level': 'ERROR', 'message': f'從url取得data失敗，使用LLM處理: {e}', 'created_at': str(datetime.now())})
            data = None
        if not data:
            try:
                data = get_data_from_url_with_llm(url)
            except Exception as e:
                insert_log_into_db(
                    {'level': 'ERROR', 'message': f'LLM處理失敗: {e}', 'created_at': str(datetime.now())})
                continue
        try:
            if not Article.objects.filter(url=data['url']).exists():
                kanban_obj, _ = Kanban.objects.get_or_create(name=data['kanban'])
                author_obj, _ = Author.objects.get_or_create(name=data['author'])
                article = Article.objects.create(
                    kanban=kanban_obj,
                    title=data['title'],
                    author=author_obj,
                    content=data['content'],
                    time=data['time'],
                    url=data['url']
                )
                article_id_list.append(article.id)
            else:
                continue
        except Exception as e:
            insert_log_into_db(
                {'level': 'ERROR', 'message': f'Data插入資料庫錯誤: {e}', 'created_at': str(datetime.now())})
        # try:
        #     store_data_in_pinecone(data)
        # except Exception as e:
        #     insert_log_into_db(
        #         {'level': 'ERROR', 'message': f'Data插入向量資料庫錯誤: {e}', 'created_at': str(datetime.now())})
    insert_log_into_db({'level': 'INFO', 'message': f'爬取 {kanban} 完成', 'created_at': str(datetime.now())})
    return article_id_list


if __name__ == '__main__':
    # kanban_list = ['Gossiping', 'car', 'Stock', 'LoL', 'home-sale']
    # for kanban in kanban_list:
    #     scrape_last_page_of_kanban(kanban)
    # print(get_data_from_url('https://www.ptt.cc/bbs/NBA/M.1743558818.A.A43.html'))
    print(get_data_from_url_with_llm('https://www.ptt.cc/bbs/NBA/M.1743558818.A.A43.html'))
    print('執行結束')
