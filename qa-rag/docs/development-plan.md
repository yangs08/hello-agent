# 开发计划书

> 基于现有 AI Agent 服务骨架的后续开发计划。

---

## 一、现状评估

### 已完成

| 模块 | 状态 | 说明 |
|------|------|------|
| Agent 编排 | ✅ 骨架完成 | ReAct + Plan-and-Execute 双模式，降级逻辑 |
| 意图识别 | ✅ 骨架完成 | 关键词匹配 + 置信度评分 |
| RAG 检索 | ✅ 骨架完成 | 三模检索 + RRF 融合 + Cross-Encoder 重排 |
| RAG 生成 | ✅ 骨架完成 | 带引用的答案生成 |
| 双层记忆 | ✅ 骨架完成 | Redis 短期 + Milvus 长期 |
| 文档 ETL | ✅ 骨架完成 | 解析 / 分块 / 入库流水线 |
| 模型路由 | ✅ 骨架完成 | 优先级 + 加权 + 熔断 |
| 语义缓存 | ✅ 骨架完成 | 余弦相似度 + 降级策略 |
| 链路追踪 | ✅ 协议抽象 | InMemoryTracer 实现 |
| API 路由 | ✅ 骨架完成 | chat / document / health |
| Docker 部署 | ✅ 完成 | compose 全栈编排 |

### 缺失 / 待完善

| 模块 | 缺失程度 | 影响 |
|------|---------|------|
| 单元测试 | ❌ 完全缺失 | 无法保证变更质量 |
| Langfuse 集成 | ❌ 完全缺失 | 无法生产可观测 |
| 离线评测框架 | ❌ 完全缺失 | 无法量化评估 RAG/Agent 质量 |
| 核心链路打通 | ⚠️ 部分缺失 | 模块间未完整串联 |
| 错误处理与重试 | ⚠️ 不完善 | Reflection 告警后无自动重试 |
| API 认证与限流 | ❌ 完全缺失 | 无法安全上线 |
| 知识块置信度 | ❌ 完全缺失 | 无法区分来源可靠性 |

---

## 二、开发路线图

### Phase 1：基础设施加固（优先级最高）

**目标**：让项目可测试、可观测、可验证

#### 1.1 单元测试覆盖

```
tests/
├── conftest.py              # 共享 fixtures
├── core/
│   ├── test_orchestrator.py # Agent 编排
│   ├── test_retriever.py    # 多路检索（mock Milvus + BM25）
│   ├── test_reranker.py     # Cross-Encoder 重排
│   ├── test_generator.py    # 答案生成 + 引用解析
│   ├── test_short_term.py   # Redis 滑动窗口 + 压缩
│   ├── test_long_term.py    # 长期记忆
│   └── test_recognizer.py   # 意图识别置信度
├── infrastructure/
│   ├── test_model_router.py # 路由 + 熔断
│   ├── test_circuit_breaker.py
│   └── test_redis_cache.py  # 语义缓存
└── api/
    └── test_chat.py         # API 集成测试
```

- 框架：pytest + pytest-asyncio
- 覆盖率目标：80%+
- 关键：所有外部依赖（Milvus / Redis / LLM）通过 mock 或 Testcontainer 隔离

#### 1.2 Langfuse 集成

**文件**：`app/infrastructure/trace/langfuse_tracer.py`

实现 `Tracer` 协议：

| 协议方法 | Langfuse 映射 |
|---------|---------------|
| `new_trace_id()` | `langfuse.trace()` |
| `start_span()` | `trace.span(name, input)` |
| `end_span()` | `span.end(output, error)` |
| `log_event()` | `trace.event(name, input)` |
| LLM 调用追踪 | `trace.generation(model, input, output, usage)` |

配置项追加到 `config.py`：
```python
langfuse_secret_key: str = ""
langfuse_public_key: str = ""
langfuse_host: str = "https://cloud.langfuse.com"
```

#### 1.3 核心链路联调

串联为完整请求路径：

```
POST /chat
  → IntentRecognizer（意图 + 置信度）
    → MemoryManager.get_context()（短期 + 长期）
      → AgentOrchestrator.run()
        → ReActAgent / PlannerAgent
          → MultiRetriever + Reranker + RAGGenerator
        → ReflectionAgent（质量评分）
    → MemoryManager.save()（写入短期）
  → 返回 AgentResponse
```

---

### Phase 2：质量与可观测（中优先级）

**目标**：量化评估、上线安心

#### 2.1 离线评测框架

```
evaluation/
├── datasets/
│   ├── rag.json       # {query, expected_answer, relevant_docs}
│   └── agent.json     # {query, expected_tool_calls, expected_answer}
├── metrics/
│   ├── faithfulness.py    # 答案是否忠实于上下文（LLM-as-judge）
│   ├── answer_relevancy.py
│   └── context_precision.py
├── runner.py          # 评测流水线编排
└── reports/
    └── report_2026-06-21.md
```

推荐指标（可用 RAGAS 库或自实现）：
- **Faithfulness**：答案 claims 是否可被检索上下文支持
- **Answer Relevancy**：答案是否回答了 query
- **Context Precision**：检索结果中相关文档占比

#### 2.2 Reflection 自动重试

当前 Reflection 只告警不行动。改进为带反馈的重生成：

```python
if report.suggest_retry and retry_count < max_retries:
    new_answer = await agent.regenerate_with_feedback(
        feedback=report.suggestions
    )
```

---

### Phase 3：安全与生产就绪

**目标**：可安全上线

- **API 认证**：API Key Bearer token 中间件
- **限流**：基于 Redis 的滑动窗口限流
- **知识块置信度**：来源权重 + 时效性衰减 → 影响检索排序

---

### Phase 4：高级功能（愿景）

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 多轮对话 TQA | 跟踪式提问-回答 | 中 |
| Agent 工具扩展 | API 调用、代码执行等 | 中 |
| 多租户隔离 | 知识库按 tenant 隔离 | 低 |
| Admin Dashboard | 会话 / 知识库管理 | 低 |

---

## 三、优先级矩阵

```
                    Importance
                   高          中          低
   ┌───────────┬───────────┬───────────┬───────────┐
   │           │  单元测试   │  离线评测   │  多租户    │
   │    高     │  Langfuse │  Reflection│           │
   │           │  链路联调   │  自动重试   │           │
   │ Urgency   ├───────────┼───────────┼───────────┤
   │           │  API 认证  │  知识块    │  Dashboard│
   │    低     │  限流      │  置信度    │  微调      │
   └───────────┴───────────┴───────────┴───────────┘
```

**推荐执行顺序**：Phase 1 → Phase 2 → Phase 3 → Phase 4

---

## 四、时间估算

| Phase | 内容 | 预估人天 |
|-------|------|---------|
| 1.1 | 单元测试覆盖 | 3-5 天 |
| 1.2 | Langfuse 集成 | 1 天 |
| 1.3 | 核心链路联调 | 1-2 天 |
| 2.1 | 离线评测框架 | 2-3 天 |
| 2.2 | Reflection 自动重试 | 1 天 |
| 3.1 | API 认证与限流 | 1-2 天 |
| 3.2 | 知识块置信度 | 2 天 |
| | **合计** | **11-16 天** |

---

## 五、技术债务记录

- `retriever.py` BM25 索引为内存实现，重启后丢失，后续可迁移到 Elasticsearch
- `pipeline.py` ETL 为同步实现，大文件处理会阻塞事件循环，后续需改为后台任务
- `orchestrator.py` InMemoryTracer 仅用于单测，生产需替换为 LangfuseTracer
- 所有 LLM 调用依赖外部 API，无 mock 时无法可靠测试
- `model_router.py` 的 weight 选择算法需更多生产验证
