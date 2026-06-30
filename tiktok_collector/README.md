# tiktok_collector

`tiktok_collector` 是当前仓库里的独立 TikTok 公网元数据采集模块。
它抓取公开视频链接和页面可见元数据，保留 JSON / CSV 导出，并支持把元数据写入 MySQL，作为后续 MySQL、MinIO、Whisper 和 AI 分析链路的上游输入。

## 当前能力

- 按关键词抓取 TikTok 搜索结果
- 每个关键词默认最多抓取 20 条
- 导出 `JSON` 和 `CSV`
- 输出清洗后的 `clean` 文件和审核报告
- 支持 FastAPI 接口调用
- 支持使用 SQLAlchemy 写入 MySQL
- `video_id` 唯一约束去重更新

## 主要字段

- `video_url`
- `video_id`
- `caption`
- `author_name`
- `author_url`
- `like_count`
- `comment_count`
- `share_count`
- `collect_count`
- `publish_time`
- `hashtags`
- `music_title`
- `cover_url`
- `source_keyword`
- `crawl_time`
- `processing_status`
- `transcript_text`
- `ai_analysis_json`
- `local_video_path`

## 目录结构

```text
tiktok_collector/
├─ .env.example
├─ README.md
├─ requirements.txt
├─ __init__.py
├─ api.py
├─ cleaner.py
├─ config.py
├─ db.py
├─ exporters.py
├─ init_db.py
├─ main.py
├─ models.py
├─ repository.py
├─ scraper.py
├─ service.py
└─ data/
   └─ raw/
      └─ .gitkeep
```

## 安装

```powershell
cd tiktok_collector
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
copy .env.example .env
```

## .env 配置

最小采集配置：

```env
TIKTOK_COLLECTOR_HEADLESS=false
TIKTOK_COLLECTOR_MAX_RESULTS=20
TIKTOK_COLLECTOR_SEARCH_SCROLLS=5
TIKTOK_COLLECTOR_SEARCH_WAIT_MS=1800
TIKTOK_COLLECTOR_VIDEO_WAIT_MS=1500
TIKTOK_COLLECTOR_MANUAL_VERIFY_WAIT_MS=90000
TIKTOK_COLLECTOR_ERROR_RETRY_COUNT=2
TIKTOK_COLLECTOR_LOCALE=en-US
TIKTOK_COLLECTOR_OUTPUT_DIR=./data/raw
TIKTOK_COLLECTOR_USER_DATA_DIR=./data/browser_profile
```

MySQL 配置：

```env
TIKTOK_COLLECTOR_MYSQL_URL=mysql+pymysql://root:password@127.0.0.1:3306/tiktok_collector?charset=utf8mb4
TIKTOK_COLLECTOR_MYSQL_ECHO=false
```

如果不配置 `TIKTOK_COLLECTOR_MYSQL_URL`，采集器会继续正常导出 JSON / CSV，但不会写入数据库。

## 初始化数据库

先确保 MySQL 中已经存在目标数据库，例如 `tiktok_collector`。

然后执行：

```powershell
cd tiktok_collector
.\.venv\Scripts\python.exe -m tiktok_collector.init_db
```

会创建 `tiktok_videos` 表。

表特性：

- 使用 SQLAlchemy ORM
- `video_id` 唯一约束
- 已包含：
  - `processing_status`，默认 `raw`
  - `transcript_text`，默认空
  - `ai_analysis_json`，默认空
  - `local_video_path`，默认空

## 本地运行

采集并导出：

```powershell
cd tiktok_collector
.\.venv\Scripts\python.exe main.py collect --keywords "wearable breast pump" "manual breast pump" "baby bottle" --limit 10
```

采集、导出并把 clean 结果导入主项目素材库：

```powershell
.\.venv\Scripts\python.exe main.py collect --keywords "wearable breast pump" "manual breast pump" "baby bottle" --limit 10 --import-workflow
```

说明：

- 如果 `.env` 里配置了 `TIKTOK_COLLECTOR_MYSQL_URL`，`collect` 成功后会自动把采集到的视频元数据写入 MySQL。
- 如果同一个 `video_id` 已存在，会更新该记录，而不是重复插入。

## API 运行

```powershell
cd tiktok_collector
.\.venv\Scripts\python.exe -m tiktok_collector.main serve --host 127.0.0.1 --port 8890
```

健康检查：

```powershell
curl http://127.0.0.1:8890/health
```

采集：

```powershell
curl -X POST http://127.0.0.1:8890/collect ^
  -H "Content-Type: application/json" ^
  -d "{\"keywords\":[\"wearable breast pump\",\"baby bottle\"],\"limit_per_keyword\":10,\"export_json\":true,\"export_csv\":true}"
```

## 输出位置

原始输出：

```text
tiktok_collector/data/raw/
```

清洗后输出：

```text
tiktok_collector/data/raw/clean/
```

文件格式：

```text
YYYYMMDDTHHMMSSZ_<keyword-slug>.json
YYYYMMDDTHHMMSSZ_<keyword-slug>.csv
YYYYMMDDTHHMMSSZ_<keyword-slug>_review.json
```

## 数据库写入说明

每次 `collect` 成功后：

- 原始采集结果先保留在内存中
- 自动写入 MySQL `tiktok_videos`
- 再继续执行 JSON / CSV / clean 文件导出

数据库中默认状态：

- `processing_status = raw`
- `transcript_text = ""`
- `ai_analysis_json = ""`
- `local_video_path = ""`

后续可以在此基础上继续接：

- Whisper 转写
- AI 分析结果回写
- 视频下载后的本地路径回填
- MySQL 到主工作流的消费逻辑
