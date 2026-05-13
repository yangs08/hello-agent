# Photo-Score

摄影图片点评系统 - 基于 LangChain + Ollama 的多模态摄影点评工具

## 架构

```
photo-score/
├── backend/          # Python FastAPI 后端
│   ├── api/          # API 路由
│   ├── core/         # 核心逻辑 (模型、链、提示词)
│   └── features/     # 功能模块
├── frontend/         # Vue 3 前端
├── data/             # 数据文件
└── docs/             # 文档
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus |
| 后端 | FastAPI + LangChain |
| 本地模型 | Ollama + minicpm-v |
| 向量库 | ChromaDB (Phase 4) |

## 运行流程

```
┌─────────────────────────────────────────────────────────────┐
│  用户浏览器  http://localhost:5173                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Vue 前端 (Vite)  :5173                                     │
│  └─ 代理 /api → http://localhost:8000                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI 后端  :8000                                        │
│  ├─ POST /api/critique   # 单张点评                         │
│  ├─ POST /api/chat       # 多轮对话                         │
│  └─ GET  /api/health     # 健康检查                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  LangChain 调用层                                           │
│  └─ ChatOllama(model="minicpm-v")                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Ollama 服务  :11434                                        │
│  └─ minicpm-v 模型 (5.5GB)                                  │
└─────────────────────────────────────────────────────────────┘
```

## 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| **Vue 前端** | `5173` | Vite 开发服务器 |
| **FastAPI 后端** | `8000` | API 服务 |
| **Ollama** | `11434` | 模型服务（默认） |

## Ollama 使用

项目通过 LangChain 调用 Ollama：

```python
# backend/core/models.py
from langchain_ollama import ChatOllama

ChatOllama(
    model="minicpm-v",                    # 模型名称
    base_url="http://localhost:11434",    # Ollama 地址
    temperature=0.7,                       # 温度参数
    num_ctx=4096                          # 上下文窗口
)
```

### 前置条件

```bash
# 安装 Ollama 后拉取模型
ollama pull minicpm-v

# 验证模型
ollama list
```

## 快速开始

### 1. 启动 Ollama

```bash
ollama serve
```

### 2. 启动后端

```bash
cd backend
pip3 install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 访问应用

浏览器打开：`http://localhost:5173`

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/critique` | 上传图片，返回点评结果 |
| POST | `/api/chat` | 多轮对话 |
| GET  | `/api/health` | 健康检查 |

## 修改端口

```python
# 后端 - backend/main.py
uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
```

```javascript
// 前端 - frontend/vite.config.js
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8080'  // 对应后端端口
    }
  }
}
```

## 功能

- [x] 单张图片点评 (4维度评分)
- [x] 多轮互动对话
- [ ] 风格蒸馏 (Phase 4)
