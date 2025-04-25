# PTT 文章爬取與 RAG 檢索系統

## 目錄


- [專案介紹](#專案介紹)
- [專案架構](#專案架構)
- [運作流程](#運作流程)
- [資料格式](#資料格式)
- [API設計](#API設計)
- [開發環境](#開發環境)
- [部署方式](#部署方式)

## 相關連結

- [專案題目](https://hackmd.io/@nickchen1998/SyOzSDW2kl)
- [觀看簡報](https://www.canva.com/design/DAGkAhFAEJo/7AMY_yvAVuhze7Bd8PFGMg/edit?utm_content=DAGkAhFAEJo&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)

---

## 專案介紹

本專案旨在爬取 PTT 指定版面的文章，並透過 **LangChain**、**Retrieval-Augmented Generation (RAG)** 技術建構智慧檢索系統。整合
**Celery + Redis** 進行非同步任務處理與排程管理，使用 **MariaDB**
儲存文章數據、**Pinecone** 進行向量檢索，並透過 **Django REST Framework (DRF)** 提供 API 服務。
此外，透過 **Docker Compose** 進行容器化部署，確保開發與部署環境的一致性。

---

## 專案架構

本專案包含以下組件：

- **爬蟲模組**：使用`BeautifulSoup`爬取 PTT 指定版面文章。
- **資料庫 (MariaDB)**：存儲爬取的文章內容、作者、發文時間等資訊。
- **非同步處理 (Celery + Redis)**: 用於排程與背景任務。
- **向量資料庫 (Pinecone)**：存儲文章的向量嵌入，用於語義檢索。
- **後端 (Django & DRF)**：提供 API 介面，供前端查詢與分析。
- **OpenAI API**：使用 LangChain 來增強查詢回應。

### 系統架構圖

![系統架構圖](https://github.com/shoukuntime/ptt_rag/blob/master/pictures/system_context_diagram.png)

### 流程圖

![排程流程圖](https://github.com/shoukuntime/ptt_rag/blob/master/pictures/period_send_ptt_scrape_task.png)
![爬蟲流程圖](https://github.com/shoukuntime/ptt_rag/blob/master/pictures/ptt_scrape.png)
![向量存入流程圖](https://github.com/shoukuntime/ptt_rag/blob/master/pictures/store_data_in_pinecone.png)

---

## 運作流程

1. **資料爬取**
    - 每小時自動執行定期執行爬蟲，擷取 PTT 文章內容。板面如下:
        1. 八卦: https://www.ptt.cc/bbs/Gossiping/index.html
        2. NBA: https://www.ptt.cc/bbs/NBA/index.html
        3. 股票: https://www.ptt.cc/bbs/Stock/index.html
        4. LoL: https://www.ptt.cc/bbs/LoL/index.html
        5. 房屋: https://www.ptt.cc/bbs/home-sale/index.html
    - 過濾重複資料，並存入 **MariaDB**。

2. **向量化處理**
    - 透過 **LangChain** 轉換文章內容為向量嵌入。
    - 儲存嵌入向量至 **Pinecone**，用於語義檢索。

3. **檢索與生成**
    - 使用 Django 提供 API，根據使用者查詢檢索最相關的 PTT 文章。
    - 利用 OpenAI API 生成回應。

---

## 資料格式

### 1. MariaDB資料表

![關聯式資料](https://github.com/shoukuntime/ptt_rag/blob/master/pictures/relational_database.png)

### `article`

| 欄位名稱      | 資料型別      | 長度  | 說明       |
|-----------|-----------|-----|----------|
| id        | BIGINT    | 20  | 主鍵，自動遞增  |
| board_id  | BIGINT    | 20  | boardID  |
| title     | VARCHAR   | 255 | 文章標題     |
| author_id | BIGINT    | 20  | authorID |
| content   | LONGTEXT  | X   | 文章內容     |
| post_time | TIMESTAMP | 6   | 發文時間     |
| url       | VARCHAR   | 255 | 文章連結     |

### `board`

| 欄位名稱 | 資料型別    | 長度  | 說明      |
|------|---------|-----|---------|
| id   | BIGINT  | 20  | 主鍵，自動遞增 |
| name | VARCHAR | 100 | 看板名稱    |

### `author`

| 欄位名稱 | 資料型別    | 長度  | 說明      |
|------|---------|-----|---------|
| id   | BIGINT  | 20  | 主鍵，自動遞增 |
| name | VARCHAR | 100 | 作者名稱    |

### `log`

| 欄位名稱       | 資料型別      | 長度  | 說明      |
|------------|-----------|-----|---------|
| id         | BIGINT    | 20  | 主鍵，自動遞增 |
| level      | VARCHAR   | 100 | 層級      |
| type       | VARCHAR   | 100 | 訊息處分類   |
| message    | LONGTEXT  | X   | 訊息      |
| traceback  | LONGTEXT  | X   | 錯誤詳細內容  |
| created_at | TIMESTAMP | 6   | 發生時間    |

### 2. Pinecone 向量格式

```json
{
   "id": "0075e0e7-3305-488d-877d-b9a223d0d09e",
   "values": [
      0.123,
      -0.456,
      0.789,
      ...
   ],
   "metadata": {
      "article_id": 1,
      "author": "rayccccc",
      "board": "Stock",
      "text": "推 oxboy25 : 推",
      "time": "Tue Nov 5 00:38:28 2024",
      "title": "Fw: [公告] 請留意新註冊帳號使用信件詐騙",
      "url": "https://www.ptt.cc/bbs/Stock/M.1730738309.A.238.html"
   }
}
```

---

## 工作拆分與時程規劃

![時程規劃圖](https://github.com/shoukuntime/ptt_rag/blob/master/pictures/schedule.png)

### 第一階段（3天）：基礎架構與環境設置

- README 文件（撰寫專案架構、運作流程、資料格式）
- 設置 Docker + Docker Compose ( MariaDB、Redis )
- 資料庫設計(MariaDB)

### 第二階段（6天）：PTT 爬蟲與資料處理、Celery 排程管理

- 開發PTT爬蟲程式(爬取指定看板文章，並一併與log存入MariaDB)
- 開發PTT文章轉向量嵌入Pinecone(使用OpenAI API、LangChain)
- 每小時執行Celery排程

### 第三階段（4天）：Django REST API

- Django REST Framework（DRF）開發(建立 API、設計 Serializer)
- 產生 Swagger API 文件

### 第四階段（4天）：系統整合與測試、優化整個專案

- 整合所有模組
- 部署與測試
- README 文件（部署）

---

## API設計

### 查詢API (GET)

- `/api/posts/`：回傳最新 50 筆文章，可透過 `limit`、`offset` 分頁，支援 `發文者`、`更新日期`、`版面` 查詢。
- `/api/posts/<id>/`：查詢特定文章詳細內容。
- `/api/statistics/`：查詢統計資訊（文章總數），可透過 `時間範圍`、`版面`、`作者` 過濾。

### RAG 檢索 API (POST)

**`POST /api/search/`**

```json
{
  "question": "請問最近台股有什麼影響市場的消息？",
  "top_k": 3
}
```

**回應範例**

```json
{
  "question": "請問最近台股有什麼影響市場的消息？",
  "answer": "根據最近 PTT 討論，台股受到美國總統川普宣布半導體關稅的影響，...",
  "related_articles": [
    {
      "id": 164,
      "board": "Stock",
      "author": "enouch777",
      "title": "[新聞] 英媒：北京握有3張底牌 抵禦川普關稅",
      "content": "原文標題：英媒：...",
      "post_time": "2025-04-15T17:34:11+08:00",
      "url": "https://www.ptt.cc/bbs/Stock/M.1744709653.A.52A.html"
    },
    {
      "id": 818,
      "board": "Gossiping",
      "author": "v40316",
      "title": "[問卦] 還沒等到川普扣訊…",
      "content": "表定今天...",
      "post_time": "2025-04-17T02:12:22+08:00",
      "url": "https://www.ptt.cc/bbs/Gossiping/M.1744827144.A.9BE.html"
    },
    {
      "id": 833,
      "board": "Stock",
      "author": "NowQmmmmmmmm",
      "title": "[情報] 聯準會主席鮑威爾今夜談話內容整理",
      "content": "繼續無視川普！...",
      "post_time": "2025-04-17T03:31:24+08:00",
      "url": "https://www.ptt.cc/bbs/Stock/M.1744831887.A.C63.html"
    }
  ]
}
```

---

## 開發環境

- Python 3.11
- Django 4.2.7
- Django REST Framework
- drf-spectacular（Swagger 文件產生）
- Celery 5.4 + Celery Beat（排程管理）

### 資料庫

- MariaDB（關聯式資料庫，使用 Docker 建置）
- Redis（快取機制，使用 Docker 部署）
- Pinecone（向量資料庫，搭配 LangChain 使用）

### 語言模型

- OpenAI GPT（公司 API Key）
- LangChain（RAG 整合）

### 開發工具

- Docker Compose（環境部署）

---

## 部署方式

1. 開啟 **Docker Desktop**

2. **運行 Docker Compose**

    - 在專案目錄cmd下執行:
       ```sh
       docker-compose up -d --build
       ```
    - 若非第一次執行可執行:
      ```sh
       docker-compose up --force-recreate -d --build
       ```

3. **資料遷移** (新建立或有修改Django models才需要)
    - 執行以下指令進入正在執行中的Docker容器裡面：
        ```sh
       docker exec -it django_web /bin/sh
       ```

    - 並執行以下指令以進行資料遷移：
        ```sh
       python manage.py makemigrations
       ```
      ```sh
      python manage.py migrate
       ```

