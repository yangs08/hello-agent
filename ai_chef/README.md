# AI Chef

会话式 AI 私厨助手。用户可以普通对话，也可以上传食材或菜品图片；系统会先判断输入是否适合给私厨建议，不合适时引导用户重新描述或重新上传，合适时再生成个性化建议。

## 功能

- 普通厨房对话：寒暄、能力说明、饮食偏好补充、烹饪常识问答。
- 图片识别：支持 `.jpg`、`.jpeg`、`.png`、`.webp`，最大 10MB。
- 输入路由：区分 `chef_ready`、`chat`、`needs_rephrase`。
- 私厨建议：结合文字、图片分析、历史对话和长期记忆输出菜品建议。
- SQLite 记忆：保存消息历史和用户偏好、忌口、过敏、厨具、近期食材。

## 目录结构

```text
ai_chef/
├── main.py              # FastAPI 应用入口，只负责装配 app 和路由
├── app/
│   ├── config.py        # 环境变量、模型名、文件限制、数据库路径
│   ├── db.py            # SQLite 初始化、消息历史、长期记忆读写
│   ├── schemas.py       # 请求流程中使用的 Pydantic 数据结构
│   ├── api/
│   │   └── routes.py    # HTTP API 路由
│   └── services/
│       ├── chef.py      # 私厨对话编排、输入判断、建议生成、记忆更新
│       └── image.py     # 图片校验和编码
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
AI_CHEF_DB_PATH=./ai_chef.sqlite3
```

## API

### `POST /chat`

`multipart/form-data` 参数：

- `user_id`: 用户 ID，默认 `default`。
- `message`: 对话内容，可为空。
- `file`: 可选图片。

返回：

```json
{
  "status": "chef_ready",
  "message": "本轮回复",
  "memory": {
    "preferences": [],
    "dislikes": [],
    "allergies": [],
    "equipment": [],
    "recent_ingredients": []
  },
  "ingredients_analysis": "图片分析",
  "recipe_suggestion": "私厨建议"
}
```

### `GET /memory/{user_id}`

读取用户长期记忆。

### `POST /analyze`

兼容旧图片分析入口，内部复用 `/chat` 流程。
