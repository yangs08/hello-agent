# 项目知识总结

> 本文档汇总了对企业级 AI Agent 服务骨架的全面分析，涵盖架构、核心模块实现原理及简历项目描述。

---

## 一、项目概况

### 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI, Uvicorn |
| Agent / LLM | LangChain, LangGraph, OpenAI 兼容 API |
| 向量数据库 | Milvus |
| 缓存 / 记忆 | Redis |
| 关系数据库 | PostgreSQL, SQLAlchemy (async) |
| 文档处理 | PyPDF, Unstructured, sentence-transformers |
| 可观测性 | Langfuse, 自定义 Tracing |
| 配置校验 | Pydantic v2, pydantic-settings |
| 部署 | Docker, docker-compose |

### 架构分层

```
┌─────────────────────────────────────────────────┐
│                  接入层                          │
│     FastAPI Routes (chat / document / health)    │
├─────────────────────────────────────────────────┤
│                  领域核心层                       │
│   Agent 编排  │  RAG 管道  │  记忆  │  工具/意图   │
│   (ReAct/Plan)│ (检索/重排) │ (短/长) │ (注册/路由)  │
├─────────────────────────────────────────────────┤
│                 基础设施层                        │
│  LLM 路由/熔断 │ 向量库  │ 缓存  │ DB  │ 可观测性   │
├─────────────────────────────────────────────────┤
│              数据 / ETL 层                       │
│         文档解析 → 分块 → 向量化 → 入库           │
└─────────────────────────────────────────────────┘
```

---

## 二、核心模块实现原理

### 2.1 Agent 编排引擎

**文件**：`app/core/agent/orchestrator.py`

支持两种模式，通过意图上下文动态选择：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| ReAct | 推理-行动-观察循环 | 工具调用类问题 |
| Plan-and-Execute | 先规划再逐步执行 | 复杂多步骤任务 |

**降级机制**：Plan 失败时自动回退 ReAct，设置 `degraded=True` 标志，保证服务可用性。

**意图识别置信度**：
- 关键词匹配公式：`min(0.95, 0.45 + 0.12 * hits)`
- 无匹配：含问号得 0.35，否则 0.25
- 阈值 0.55，低于时触发澄清提示

### 2.2 多路 RAG 管道

**文件**：`app/core/rag/retriever.py`, `reranker.py`, `generator.py`

三层递进评分：

```
用户查询
    ├──→ 向量检索（Milvus L2 距离）
    ├──→ BM25 关键词检索（k1=1.5, b=0.75）
    └──→ 混合检索（RRF 融合, k=60）
              ↓
         Cross-Encoder 重排序
```

**文档 ETL 流程**：
```
上传 → 解析(TXT/PDF) → 分块(Fixed/Recursive/Paragraph) → 向量化 → 入库
```

### 2.3 双层记忆系统

**文件**：`app/core/memory/short_term.py`, `long_term.py`, `manager.py`

| 维度 | 短期记忆 | 长期记忆 |
|------|---------|---------|
| 存储 | Redis List | Milvus Collection |
| 容量 | 20 条 / 4000 tokens | 无上限 |
| 超量策略 | LLM 自动摘要压缩 | — |
| 检索 | 顺序读取 | 语义相似度召回 |
| 生命周期 | 随会话结束 | 持久化，可主动 forget |

`MemoryManager` 统一协调两者，`get_context()` 同时获取短期历史 + 长期召回。

### 2.4 多模型路由 + 熔断降级

**文件**：`app/infrastructure/llm/model_router.py`, `circuit_breaker.py`

三层机制：

1. **优先级调度**：按 `priority` 升序分组，高优先级优先尝试
2. **加权负载均衡**：同优先级内 `random()^(1/weight)` 加权随机排序
3. **熔断降级**：三状态（CLOSED → OPEN → HALF_OPEN），5 次失败阈值，60s 恢复超时

```
候选列表 → 遍历尝试 → 熔断跳过失败模型 → 降级下一候选 → 全部失败报错
```

### 2.5 语义缓存

**文件**：`app/infrastructure/cache/redis_cache.py`

不靠精确 key 匹配，而是比较 query 间的语义相似度：

```
写入：hash(query) → encode 向量 → 存 {query_text, value, embedding}
读取：encode 输入 → 遍历索引 → 余弦相似度匹配 → >= 0.95 命中
```

降级策略：无 SentenceTransformer 时使用 bigram hash（256 维）+ Jaccard 相似度。

### 2.6 反射（Reflection）机制

**文件**：`app/core/agent/reflection.py`

Agent 回答后，由 ReflectionAgent 进行质量审查：

- 评分维度：完整性、幻觉风险、证据一致性
- LLM 输出 JSON：`{quality_score: 0-100, likely_hallucination: bool, ...}`
- 低于阈值（默认 60）触发告警

### 2.7 置信度体系全景

| 子系统 | 指标 | 范围 | 用途 |
|--------|------|------|------|
| 意图识别 | confidence | [0.0, 1.0] | 是否触发澄清 |
| 输出质量 | quality_score | [0, 100] | 答案质量评估 |
| 向量检索 | L2 distance | 无界 | 语义相似度排序 |
| BM25 | Okapi score | 无界 | 关键词相关性 |
| 语义缓存 | cosine similarity | [0, 1] | 缓存命中判断 |
| 熔断器 | state | 三态 enum | LLM 是否可用 |
| 模型路由 | weight | [0, ∞) | 负载分配概率 |

---

## 三、简历项目描述

### 精简版

**企业级 AI Agent 服务**　｜　FastAPI / LangChain / LangGraph / Milvus / Redis / PostgreSQL / Langfuse

- 设计并实现双模式 Agent 编排引擎（ReAct + Plan-and-Execute），集成意图识别置信度评分与自动降级，保障服务可用性
- 构建多路 RAG 管道（向量检索 + BM25 关键词 + RRF 融合 + Cross-Encoder 重排），配套完整 ETL 文档处理流水线
- 实现双层记忆系统：Redis 滑动窗口短期记忆（超阈值自动 LLM 摘要压缩）+ Milvus 向量长期记忆（按会话语义召回）
- 搭建生产级基础设施：多模型路由（优先级调度 + 加权负载均衡 + 熔断降级）、语义缓存（余弦相似度 0.95 近似命中）、Langfuse 链路追踪
- 引入 Reflection 反思机制对输出进行质量评分与幻觉检测，搭建离线评测框架自动化评估 RAG 忠实度等指标

---

## 四、待实现事项

- [ ] Langfuse 集成：实现 LangfuseTracer，对接现有 Tracer 协议
- [ ] 离线评测框架：测试数据集 + 自动化评估指标（RAGAS / LLM-as-judge）
