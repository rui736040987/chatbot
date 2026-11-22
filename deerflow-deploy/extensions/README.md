# 本地 PDF 引用扩展

`pdf_citations` 是本项目新增的独立扩展，**不是上游自带功能，也不是纯配置实现**。它继承未改动的官方 WeKnora Provider，通过 DeerFlow 现有 `knowledge_provider`、`routers` 扩展接口注册。两个上游 Git 仓库保持干净。

## 流程

1. `build_pdf_catalog.py` 根据 `.local/pdf-sources.json` 清单用 PDFium 读取原始 PDF，按物理页序保存正文、原文件及 SHA256。目录位于 `.local/deerflow-runtime/pdf-catalog`，仅以只读方式挂载。
2. 普通 `knowledge_search` 仍访问现有 WeKnora 的 KB-bound hybrid-search，并沿用其用户、KB、文档过滤及授权检查。
3. 对有本地原件的命中，将正文规范化（Unicode NFKC、小写、去掉非字母数字字符），通过 24 字符索引找候选页面，再要求至少 64 字符连续匹配。仅对实际匹配到的页面返回原文摘录与定位。跨页可返回两个来源；不匹配的保留无页码来源。
4. MCP 原文可通过同一个 `knowledge_search` 调用：`pdf-evidence {"document_id":"原生UUID","quote":"连续原文"}`。引文至少包含 40 个规范化字符，必须完整出现在某一页。此分支是本地原件精确核验，**不调用向量搜索**；仍实时检查 WeKnora 授权和当前回合的知识库/文档范围。
5. 返回标准 `KnowledgeSource` 的 `page`/`url` 与原文对应摘录，使用上游共享引用格式化与证据预算。`hit.content` 必须等于 `source.excerpt`，否则上游会丢弃引用。
6. PDF GET 接口位于 `/api/plugins/pdf-citations/documents/{id}`，使用现有会话认证及实时文档授权；输出 inline PDF，支持 HTTP Range。URL 的 `#page=N` 由浏览器原生 PDF 阅读器处理。

页码始终指 **从 1 开始的原始 PDF 物理页**，不取自页脚，不代表文档印刷页标签。该实现提供页级定位，不提供框选高亮。

## Wiki 联合取证（2026-11-10）

启用现有 `knowledge_entries_search` 工具，并在 WeKnora MCP 端点开放
`wiki_index`、`wiki_search`、`wiki_read_page`。原先未配置这些入口，并非上游不支持 Wiki。

本地 Provider 的 `entries_search` 使用原生 Wiki API：普通关键词返回最多三个已发布页面的摘要、来源文档 ID 和首批直接关联证据；
`wiki-page {"knowledge_base_id":"...","slug":"entity/ch340c","offset":0,"limit":6}`
返回完整 Wiki 正文及分页关联的 chunk。继续增大 offset 可补读后续证据，单次 limit 最大 12。
Wiki 引用打开 WeKnora 的 `?tab=wiki&slug=...` 页面。原文引用通过 `chunk_refs` 读取当前 chunk，验证其知识库及来源文档归属，
将 `source_locators` 中 exact PDF 引用按物理页分组，保留定位器的原文 quote；校验 source_hash 与本地 PDF MD5 一致后才产生页码链接。
没有精确定位或文件版本不一致时，仅返回无页码原文证据。Wiki 支持知识库范围，拒绝文档级过滤，不扩大范围。

原有普通 chunk 检索仍保留文本匹配定位；新的 Wiki 证据路径使用 WeKnora 原生定位，不猜测页码。
问答提示词要求跨章节/概览/比较问题同时取 Wiki 和原文，模型负责选择主题并分页补证；不是保证每轮自动穷尽全部页面的检索器。

## 重建与验证命令

宿主需要 Python 3 和 `pypdfium2`：

```bash
cd /home/caorui/workspace/xfusion/chatbot
python3 deerflow-deploy/build_pdf_catalog.py
docker compose -f deerflow-deploy/compose.yaml restart gateway
docker exec chatbot-deerflow-gateway-1 /app/backend/.venv/bin/python /opt/local-extensions/test_pdf_citations.py
```

本地目录是当前 11 份原件的快照；新增/替换文档后需更新构建清单并重建。没有原件、OCR 与原文不一致、纯图像描述等情况不强行生成页码。普通检索仍受原有召回质量影响；多个 KB 的结果可能先占满证据预算，建议在 UI 选定目标知识库。旧会话不会自动改写，需要重新取证回答。

URL 默认使用本机地址；迁移域名通过 `DEERFLOW_PUBLIC_URL` 和 `WEKNORA_PUBLIC_URL` 环境变量设置。下载授权沿用当前用户对 `chip-docs` 的连接绑定，单次聊天的选择范围仅用于取证，不是用户的永久文档 ACL。

## 网页验收记录（2026-11-10）

- CH340C 跨功能、电气参数、应用章节： http://localhost:2026/workspace/agents/chip-docs/chats/e05d0fa3-6f32-42ac-8be3-1a53b8c13811 。限定嘉立创库，5次工具调用，包含Wiki检索、关联证据分页和原文检索。首版末尾自行构造了无效域名，随后在同一会话明确纠正为工具原始引用句柄。
- W25Q32JV 0Bh指令/时序与AC参数： http://localhost:2026/workspace/agents/chip-docs/chats/68e49c36-7e7c-4eef-82f0-c6be50b9e8da 。调用Wiki和原文工具；实际点击Wiki实体页及PDF物理页29/76、63/76，浏览器显示对应内容。首版dummy状态及计数表达经同一会话复核修正。
- 证据位于 `deerflow-deploy/evidence/wiki/`：工具记录JSON和网页截图；5项引用/权限/版本校验测试通过。
- 初期测试发现WSL宿主embedding网关未启动，已运行现有start-services.sh恢复。CH340第一轮出现重复检索，已终止该测试；最终复测限定知识库和工具次数。不能据此宣称模型每次自动回答都正确或检索次数稳定。
- Wiki网页需要单独登录WeKnora；首次登录可能回到知识库列表，登录后重新点击来源链接即可。PDF沿用DeerFlow会话。RM0090尚无Wiki，此次没有为千页手册生成Wiki。
