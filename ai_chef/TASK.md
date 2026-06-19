# AI Chef Task List

## Done

- [x] 支持统一 `/chat` 会话入口。
- [x] 支持文字对话和可选图片上传。
- [x] 让 LangChain agent 在会话内判断普通对话、补充引导和私厨建议。
- [x] 输入不适合时引导用户重新对话或重新上传图片。
- [x] 输入适合时生成私厨建议。
- [x] 使用 LangChain agent 生成对话和私厨建议。
- [x] 使用 LangGraph SQLite checkpointer 保存多会话记忆。
- [x] 使用 LangChain SummarizationMiddleware 做 10 轮压缩和 3000 token 上下文控制。
- [x] 使用 SQLite 保存审计消息和会话列表。
- [x] 使用 `resource/` 保存 SQLite 数据和上传图片。
- [x] 保存图片原始文件、图片元数据和消息关联。
- [x] 保留 `/analyze` 图片分析兼容接口。

## Next

- [ ] 增加端到端测试用例。
- [ ] 增加前端聊天界面。
- [ ] 支持用户主动清除或编辑记忆。
