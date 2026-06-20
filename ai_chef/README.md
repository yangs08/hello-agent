# AI Chef

会话式 AI 私厨助手。用户可以普通对话，也可以上传食材或菜品图片；系统会先判断输入是否适合给私厨建议，不合适时引导用户重新描述或重新上传，合适时再生成个性化建议。

## 功能

- 普通厨房对话：寒暄、能力说明、饮食偏好补充、烹饪常识问答。
- 图片识别：支持 `.jpg`、`.jpeg`、`.png`、`.webp`，最大 10MB。
- Agent 自主判断：普通对话直接回应，输入不足时引导补充，输入足够时给私厨建议。
- 私厨建议：结合文字、会话上下文和按需图片分析输出菜品建议。
- 图片理解：主 agent 模型直接接收并理解图片；需要将 `AI_CHEF_TEXT_MODEL` 配成支持多模态输入的模型。
- Tavily 视频搜索：agent 知道食材后可调用 `web_search` 搜索料理视频候选，自己评估可行性并取前 3 个。
- LangGraph SQLite 会话记忆：每个 `session_id` 对应一个独立会话窗口。
- LangChain 压缩记忆：10 条消息后触发压缩，保留约 3000 token 上下文。
- LangSmith tracing：开启后可观察 agent、模型调用、工具调用和每个会话的 trace。
- 本地资源存储：SQLite 数据和上传图片统一放在 `resource/` 目录。
- 上传/对话分离：前端优先获取 OSS 临时凭证直传图片，再把 OSS URL 发给 `/chat`；`/uploads` 保留为本地开发/兜底。

## 目录结构

```text
ai_chef/
├── main.py              # FastAPI 应用入口，只负责装配 app 和路由
├── app/
│   ├── config.py        # 环境变量、模型名、文件限制、数据库路径
│   ├── db.py            # SQLite 初始化、审计消息、会话列表
│   ├── observability.py # LangSmith tracing 配置
│   ├── schemas.py       # 请求流程中使用的 Pydantic 数据结构
│   ├── agents/
│   │   └── chef/
│   │       ├── agent.py   # 创建 LangChain agent
│   │       ├── memory.py  # LangGraph SQLite checkpoint 和压缩记忆
│   │       ├── models.py  # 文本模型、视觉模型初始化
│   │       ├── prompts.py # 私厨 agent system prompt
│   │       ├── runner.py  # agent invoke、LangSmith run metadata
│   │       └── tools.py   # web_search 等工具
│   ├── api/
│   │   └── routes.py    # HTTP API 路由
│   └── services/
│       ├── chef.py      # 产品侧 chat 流程、消息审计和响应组装
│       ├── image.py     # 图片校验和编码
│       └── storage.py   # 上传图片文件持久化
├── resource/            # 本地运行数据，默认不提交
│   ├── ai_chef.sqlite3
│   ├── langgraph_checkpoints.sqlite3
│   └── uploads/
├── README.md
├── TASK.md
├── pyproject.toml
└── uv.lock
```

## 启动

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

默认使用本地 Ollama OpenAI-compatible 接口：

```bash
OLLAMA_BASE_URL=http://localhost:11434/v1
AI_CHEF_VISION_MODEL=minicpm-v
AI_CHEF_TEXT_MODEL=qwen2.5:7b
TAVILY_API_KEY=your-tavily-api-key
LANGSMITH_TRACING=true
# 兼容旧配置名：LANGSMITH_TRACKING=true
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=ai-chef
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_CALLBACKS_BACKGROUND=true
AI_CHEF_RESOURCE_DIR=./resource
AI_CHEF_DB_PATH=./resource/ai_chef.sqlite3
AI_CHEF_CHECKPOINT_DB_PATH=./resource/langgraph_checkpoints.sqlite3
```

图片默认存本地 `resource/uploads`。如果要上传到阿里云 OSS：

```bash
AI_CHEF_STORAGE_BACKEND=oss
ALIYUN_OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_BUCKET=your-bucket
ALIYUN_OSS_ACCESS_KEY_ID=your-access-key-id
ALIYUN_OSS_ACCESS_KEY_SECRET=your-access-key-secret
ALIYUN_OSS_ROLE_ARN=acs:ram::1234567890:role/your-upload-role
# 使用 STS 时配置
ALIYUN_OSS_SECURITY_TOKEN=your-security-token
# 可选：绑定 CDN 或自定义域名
ALIYUN_OSS_PUBLIC_BASE_URL=https://cdn.example.com
ALIYUN_OSS_OBJECT_PREFIX=ai-chef/uploads
ALIYUN_OSS_STS_DURATION_SECONDS=1800
```

前端直传 OSS 需要在 OSS bucket 配置 CORS，至少允许你的前端 Origin、`POST` 方法，以及 `x-oss-security-token` 请求头。

`LANGSMITH_TRACING=false` 时不会上报 trace；开启后，`/chat` 每次调用会用 `session_id` 写入 trace metadata，方便之后按会话窗口过滤。

## API

### `POST /chat`

`application/json` 请求体：

- `session_id`: 会话 ID，默认 `default`。不同 `session_id` 拥有不同会话上下文。
- `message`: 唯一业务输入，可以是普通文字，也可以是包含文字和图片的 content 数组。

纯文字：

```json
{
  "session_id": "default",
  "message": "今晚两个人，想做快手晚餐"
}
```

文字 + 已上传图片 URL：

```json
{
  "session_id": "default",
  "message": [
    { "type": "text", "text": "能做什么菜？" },
    { "type": "image", "url": "/images/1" }
  ]
}
```

文字 + base64 图片：

```json
{
  "session_id": "default",
  "message": [
    { "type": "text", "text": "能做什么菜？" },
    { "type": "image", "data": "iVBORw0KGgo..." }
  ]
}
```

返回：

```json
{
  "status": "chat",
  "session_id": "default",
  "message": "本轮回复"
}
```

### `POST /oss/upload-token`

获取前端直传 OSS 的临时上传参数。

```json
{
  "filename": "food.jpg",
  "content_type": "image/jpeg"
}
```

返回：

```json
{
  "access_key_id": "...",
  "security_token": "...",
  "expiration": "...",
  "policy": "...",
  "signature": "...",
  "bucket": "your-bucket",
  "endpoint": "https://oss-cn-hangzhou.aliyuncs.com",
  "object_key": "ai-chef/uploads/xxx.jpg",
  "url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/ai-chef/uploads/xxx.jpg"
}
```

前端上传成功后调用 `POST /images/register` 保存图片记录。

### `POST /images/register`

登记已上传到 OSS 的图片。

```json
{
  "session_id": "default",
  "filename": "food.jpg",
  "content_type": "image/jpeg",
  "storage_path": "ai-chef/uploads/xxx.jpg",
  "url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/ai-chef/uploads/xxx.jpg",
  "size_bytes": 12345
}
```

### `POST /uploads`

服务端代传图片并返回可用于 `/chat` 的 URL。这个接口保留给本地开发或 OSS 直传失败时兜底。

`multipart/form-data` 参数：

- `session_id`: 会话 ID，默认 `default`。
- `file`: 图片文件。

返回：

```json
{
  "url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/ai-chef/uploads/xxx.jpg",
  "image": {
    "id": 1,
    "session_id": "default",
    "filename": "food.jpg",
    "content_type": "image/jpeg",
    "storage_path": "ai-chef/uploads/xxx.jpg",
    "url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/ai-chef/uploads/xxx.jpg",
    "size_bytes": 12345,
    "created_at": "..."
  }
}
```

### `GET /sessions`

列出已有会话窗口。

### `GET /sessions/{session_id}/messages`

列出某个会话窗口的产品侧历史记录。

### `GET /images/{image_id}`

读取上传图片原图。

### `POST /analyze`

兼容旧图片分析入口，内部复用 `/chat` 流程，返回 `recipe_suggestion`。
