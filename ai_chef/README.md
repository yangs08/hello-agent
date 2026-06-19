# AI Chef

会话式 AI 私厨助手。用户可以普通对话，也可以上传食材或菜品图片；系统会先判断输入是否适合给私厨建议，不合适时引导用户重新描述或重新上传，合适时再生成个性化建议。

## 功能

- 普通厨房对话：寒暄、能力说明、饮食偏好补充、烹饪常识问答。
- 图片识别：支持 `.jpg`、`.jpeg`、`.png`、`.webp`，最大 10MB。
- Agent 自主判断：普通对话直接回应，输入不足时引导补充，输入足够时给私厨建议。
- 私厨建议：结合文字、会话上下文和按需图片分析输出菜品建议。
- 图片工具调用：上传图片先保存资源，agent 需要视觉信息时再调用 `analyze_image` 工具分析。
- Tavily 视频搜索：agent 知道食材后可调用 `web_search` 搜索料理视频候选，自己评估可行性并取前 3 个。
- LangGraph SQLite 会话记忆：每个 `session_id` 对应一个独立会话窗口。
- LangChain 压缩记忆：10 条消息后触发压缩，保留约 3000 token 上下文。
- 本地资源存储：SQLite 数据和上传图片统一放在 `resource/` 目录。
- 上传/对话分离：图片先通过 `/uploads` 换取 URL，`/chat` 只接收 URL。

## 目录结构

```text
ai_chef/
├── main.py              # FastAPI 应用入口，只负责装配 app 和路由
├── app/
│   ├── config.py        # 环境变量、模型名、文件限制、数据库路径
│   ├── db.py            # SQLite 初始化、审计消息、会话列表
│   ├── schemas.py       # 请求流程中使用的 Pydantic 数据结构
│   ├── api/
│   │   └── routes.py    # HTTP API 路由
│   └── services/
│       ├── chef.py      # LangChain agent 编排、输入判断、建议生成、会话记忆
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
AI_CHEF_RESOURCE_DIR=./resource
AI_CHEF_DB_PATH=./resource/ai_chef.sqlite3
AI_CHEF_CHECKPOINT_DB_PATH=./resource/langgraph_checkpoints.sqlite3
```

## API

### `POST /chat`

`multipart/form-data` 参数：

- `session_id`: 会话 ID，默认 `default`。不同 `session_id` 拥有不同会话上下文。
- `message`: 对话内容，可为空。
- `url`: 可选图片 URL，由 `/uploads` 返回。

返回：

```json
{
  "status": "chat",
  "session_id": "default",
  "message": "本轮回复",
  "url": "/images/1",
  "ingredients_analysis": "图片分析",
  "recipe_suggestion": null
}
```

### `POST /uploads`

上传图片并返回可用于 `/chat` 的 URL。

`multipart/form-data` 参数：

- `session_id`: 会话 ID，默认 `default`。
- `file`: 图片文件。

返回：

```json
{
  "url": "/images/1",
  "image": {
    "id": 1,
    "session_id": "default",
    "filename": "food.jpg",
    "content_type": "image/jpeg",
    "storage_path": ".../resource/uploads/xxx.jpg",
    "url": "/images/1",
    "size_bytes": 12345,
    "created_at": "..."
  }
}
```

### `GET /sessions`

列出已有会话窗口。

### `GET /sessions/{session_id}/messages`

列出某个会话窗口的产品侧历史记录，包括图片 URL、文件名、存储路径和图片分析。图片分析在 agent 调用工具后才会回填。

### `GET /images/{image_id}`

读取上传图片原图。

### `POST /analyze`

兼容旧图片分析入口，内部复用 `/chat` 流程。
