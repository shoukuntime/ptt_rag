# PTT 文章爬取與 RAG 檢索系統

## 目錄

- [專案介紹](#專案介紹)
- [專案架構](#專案架構)
- [運作流程](#運作流程)
- [資料格式](#資料格式)
- [API設計](#API設計)
- [開發環境](#開發環境)
- [部署方式](#部署方式)

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

### 排程流程圖

![排程架構圖](https://github.com/shoukuntime/ptt_rag/blob/master/pictures/period_send_ptt_scrape_task.png)


---

## 運作流程

1. **資料爬取**
    - 每小時自動執行定期執行爬蟲，擷取 PTT 文章內容。板面如下:
        1. 八卦: https://www.ptt.cc/bbs/Gossiping/index.html
        2. 汽車: https://www.ptt.cc/bbs/car/index.html
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

| 欄位名稱      | 資料型別      | 說明       |
|-----------|-----------|----------|
| id        | BIGINT    | 主鍵，自動遞增  |
| board_id  | BIGINT    | boardID |
| title     | VARCHAR   | 文章標題     |
| author_id | BIGINT    | authorID |
| content   | LONGTEXT  | 文章內容     |
| post_time | TIMESTAMP | 發文時間     |
| url       | VARCHAR   | 文章連結     |

### `board`

| 欄位名稱 | 資料型別    | 說明      |
|------|---------|---------|
| id   | BIGINT  | 主鍵，自動遞增 |
| name | VARCHAR | 看板名稱    |

### `author`

| 欄位名稱 | 資料型別    | 說明      |
|------|---------|---------|
| id   | BIGINT  | 主鍵，自動遞增 |
| name | VARCHAR | 作者名稱    |

### `log`

| 欄位名稱       | 資料型別      | 說明      |
|------------|-----------|---------|
| id         | INT       | 主鍵，自動遞增 |
| level      | VARCHAR   | 層級      |
| type       | VARCHAR   | 流程階段    |
| message    | LONGTEXT  | 訊息      |
| traceback  | LONGTEXT  | 錯誤詳細內容  |
| created_at | TIMESTAMP | 發生時間    |

### 2. Pinecone 向量格式

```json
{
  "id": "0075e0e7-3305-488d-877d-b9a223d0d09e",
  "values": [0.123, -0.456, 0.789, ...],
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

- README 文件（初步撰寫）
    - 撰寫專案架構、運作流程、資料格式
    - 確保有基本的環境說明，方便後續開發
- 部署與容器化
    - 設置 Docker + Docker Compose
        - MariaDB
        - Redis
    - 測試 MariaDB、Redis 服務是否可正常啟動與運作
- 資料庫設計
    - 設計 MariaDB 資料表架構
    - 透過 Docker 啟動 MariaDB，並測試基本的資料讀寫

### 第二階段（3天）：PTT 爬蟲與資料處理

- PTT 爬蟲開發
    - 開發 PTT 爬蟲程式（爬取最新文章、去重複）
    - 爬取指定看板文章，並存入 MariaDB
    - 設計爬蟲 log 紀錄機制，存入 MariaDB
- 向量資料庫與 OpenAI API
    - 申請 Pinecone 帳號，設定向量資料庫
    - 開發 PTT 文章轉向量嵌入
    - 申請 OpenAI API Key，設定 LangChain

### 第三階段（2天）：Celery 排程管理

- 定期執行排程
    - 設置 `Celery + Celery Beat`
    - 每小時執行一次爬蟲，並存入 MariaDB
    - 撰寫測試案例，確保定時執行功能正常
    - 確保爬蟲與log可穩定運行至少 3 天

### 第四階段（4天）：Django REST API

- Django REST Framework（DRF）開發
    - 建立 API：
        - 文章數據`查詢`
        - `篩選`條件（標題、時間、關鍵字）
        - `增刪改`功能
    - 設計 Serializer 進行資料驗證與請求參數處理
- API 文件（Swagger）
    - 使用 `drf-spectacular` 產生 OpenAPI 3.0 規格的 Swagger 文件
    - 為所有 API 端點提供詳細描述、請求參數、回應格式
    - 撰寫 /api/search/ API：
        - 接受使用者的自然語言問題
        - 使用向量檢索找出最相關文章
        - 透過 OpenAI LLM 生成基於文章內容的回答

### 第五階段（2天）：系統整合與測試

- 整合所有模組
    - 爬蟲 → 存入資料庫
    - API 查詢文章
    - 向量檢索 → 生成回應
- 部署與測試
    - 使用 Docker + Docker Compose 部署整個專案
    - 進行負載測試與錯誤修正
- README 文件（最終補充）
    - 新增完整的部署與執行指引
    - 確保所有開發人員可以順利運行系統

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
  "query": "請問最近台股有什麼影響市場的消息？"
}
```

**回應範例**

```json
{
  "question": "請問最近台股有什麼影響市場的消息？",
  "related_articles": [
    {
      "id": 123,
      "title": "台股暴跌原因分析",
      "url": "https://ptt.cc/article/123"
    },
    {
      "id": 456,
      "title": "市場對通膨數據的反應",
      "url": "https://ptt.cc/article/456"
    }
  ],
  "response": "根據最近 PTT 討論，市場受到國際通膨數據影響，導致台股波動..."
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

- Napkin AI（流程圖與架構設計）
- Docker Compose（環境部署）

---

## 部署方式

1. **運行 Docker Compose**
   ```sh
   docker-compose up -d
   ```
2. **啟動 Celery Worker**
   ```sh
   celery -A ptt_rag worker -P eventlet -l info
   ```
3. **啟動 Celery Beat（排程管理）**
   ```sh
   celery -A ptt_rag beat -l info
   ```
4. **啟動 Django 伺服器**
   ```sh
   python manage.py runserver
   ```

