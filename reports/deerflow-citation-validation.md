# DeerFlow 引用跳转与 PDF 页码定位复验

日期：2026-11-01。环境：WSL Ubuntu Linux Docker；入口 http://localhost:2026/workspace/agents 。

## 实现性质

此前部署、模型、知识库和智能体接入通过配置、部署辅助脚本与上游现有扩展完成，没有修改 DeerFlow/WeKnora 上游代码。本轮检查确认：上游前端已有 `KnowledgeSource.url/page` 展示能力，但自带 WeKnora Provider 明确留空，并无配置开关补齐。因此本轮**新增了本地扩展代码**，不是纯配置实现；两个上游仓库仍无修改。

本地实现位于 `deerflow-deploy/extensions/pdf_citations/__init__.py`，继承官方只读 Provider，使用现有 `knowledge_provider` 和 `routers` 插件接口，不改上游前后端、不重建官方镜像、不直接修改数据库。Compose 新增两个只读挂载并改用本地扩展安装入口；模型仍为 OpenCode Go，WeKnora 原有知识库和 MCP 继续使用。

## 页码与引用如何生成

1. 用 PDFium 对当前 11 份原始 PDF 建立按物理页序的正文目录，总计 2028 页。其中 RM0090 为 1749 页。原件副本与 SHA256 保存于私有运行目录，不进入上游仓库。
2. 普通检索照常调用 WeKnora 的知识库检索，保留其用户、知识库、文档范围检查。对能与原始页面正文连续匹配的结果，生成对应页面的原文摘录，填入来源的 `page` 和 `url`；匹配不足的来源继续没有页码。
3. 普通分块可跨页。候选页通过规范化正文的长连续匹配确定，最多为一条命中拆成两个页面来源；不拿相邻页脚当当前内容页码。引用摘要围绕匹配原文截取，避免只返回无关页眉。
4. MCP 读取结果本身不带 DeerFlow 标准引用。本地扩展提供 `knowledge_search` 的 `pdf-evidence {document_id, quote}` 查询格式：先实时检查 WeKnora 访问权限及本轮选中的知识库/文档，再要求连续引文完整存在于某一原始 PDF 页面。匹配成功才返回标准引用句柄。该分支是本地 PDF 精确核验，不调用向量检索，也不是让 WeKnora 的 `ask` 代答。
5. 仍由 DeerFlow 原生格式化器校验证据、控制长度和生成 `#knowledge-source-…` 句柄。前端原生引用卡片显示摘录、页码和真实 URL；点击 URL 打开同域、需登录的 PDF GET 接口，浏览器原生阅读器处理 `#page=N`。
6. PDF 接口同时检查当前登录身份与现有 WeKnora 文档权限，支持 HTTP Range，返回 inline PDF；不在 URL 中放模型或知识库密钥。

**页码指原始 PDF 从 1 开始的物理页，不是模型推算的页脚标签。当前只定位到页，不高亮原文矩形区域。**

## 网页实际验收

浏览器技能：`agent-browser`，独立会话 `deerflow-citations`。先在网页登录，再选定目标知识库、提交真实问题、点击回答中的来源卡片、点击卡片 URL，观察原生 PDF 阅读器页码框和页面内容。不是只检查 API 的 URL 字符串。

| 验证项 | 实际结果 | 证据 |
|---|---|---|
| CH340C 晶振与 V3 接法 | 选定嘉立创知识库，回答不需外部晶振，5V 时 V3 仅接退耦电容，3.3V 时 V3/VCC 相连。点击 V3 来源后，原 PDF 阅读器显示 **3/10** | `parameters-source.png`、`parameters-pdf-page3.png` |
| RM0090 DMAEN 定义 | 标准来源卡片跳转完整原 PDF，阅读器显示 **1066/1749**；页面含 SDIO_DCTRL 和 bit3 DMAEN 的 0/1 定义 | `large-source1066.png`、`large-pdf1066-fit.png` |
| RM0090 DMA 请求映射表 | 补查 Table43 的真实 Channel4 行并核验，引用打开 **308/1749**；该页是 DMA2 request mapping 表 | `large-source308.png`、`large-pdf308-fit.png`、`large-pdf308-snapshot.txt` |
| 跨章节回答 | 最终分别引用 **308** 页与 **1066** 页，回答 DMA2、Stream3/6、Channel4，DMAEN bit3、0禁用1使能 | `large-final-answer.png`、`large-final-state.json` |
| 新会话普通提问 | 不在用户问题中提供定位格式或答案，助手按配置自动调用MCP及pdf-evidence，成功生成308/1066引用；分别点击后原PDF页码框正确 | `fresh-large-state.json`、`fresh-pdf308-snapshot.txt`、`fresh-pdf1066-snapshot.txt` |
| PDF 会话鉴权 | 已登录 Range GET 为206，正文以 `%PDF` 开头；未登录为401 | `verification-summary.json` |
| 自动检查 | 4项测试通过，覆盖真实跨页分块、虚构证据无定位、MCP引文到共享引用格式，以及未绑定用户/禁用范围/错误KB/错误文档过滤均不能绕过 | `contract-tests.txt` |

验收对话：

- 参数：[CH340C 验证](http://localhost:2026/workspace/agents/chip-docs/chats/f5bb0669-3121-4514-bac6-770436e6feb1)。
- 新会话直接复验：[普通提问](http://localhost:2026/workspace/agents/chip-docs/chats/39b9dbdb-ffbc-40b7-aa26-abac1e74d1d0)，单轮运行成功，页面取证使用17步左右工具调用，约两分钟；原问题没有提供答案、页码或扩展定位指令。
- 千页与引用补查：[RM0090 验证](http://localhost:2026/workspace/agents/chip-docs/chats/7dcb5f32-86b7-4167-9897-13432181f814)。

## 保留的失败与限制

- 初次“所有知识库”检索时，无关的 RM0090 结果先占满来源预算，模型错误地说知识库没有 CH340C。该轮保留于 `initial-all-scope-state.json`；选定目标嘉立创知识库后成功。当前页定位扩展不等于已修复原有检索召回问题。
- 本地扩展开发早期，来源摘录与命中正文不完全一致，上游正确剥离了该引用。已改为二者严格一致，并用共享来源读回测试验证；不能只凭 Provider 返回 URL 就宣布前端引用可用。
- 千页第一轮普通向量检索反复漏召回 MCP 已读证据，手动在网页停止，状态保留 interrupted。随后加入精确引文核验入口，网页追问后成功。
- 第一条可跳转的 DMA 配置来源是第1034页 SDIO 操作流程，支持结论但不满足“DMA请求映射表章节”的验收要求；因此继续追问取得真实映射表第308页，最终保留两章来源。不是初次回答自动全通过。
- 未与原件文本匹配的来源（例如生成的图片描述、扫描图、OCR差异较大段落）不强行给页码。此前图片上传问答及图面识别能力保持原状；本轮未声称实现任意图片描述自动回溯到原 PDF。
- 新会话自动完成了主要结论和跳转，但额外说明“页眉页码与物理页不同”的表述不准确：本例308、1066页恰好与印刷页标相同。页定位证据以实际PDF阅读器和来源字段为准，不采用该附加推断。引用功能验证不等于整段模型回答无误。
- 当前目录是11份原件的本地快照。新增或替换知识文档需更新清单并重建目录；不具备自动同步能力。旧回答的错误锚点不会被静默改写，需重新取证。
- 页定位是规范化正文匹配，对标点/空白不敏感；它证明引文位于该页，不证明模型对表格列、连线或技术含义的推理必然正确。
- 本机 URL 固定为 localhost:2026，迁移域名需调整本地扩展。下载按当前登录用户对已绑定 chip-docs 的文档访问授权，不把聊天临时选择当永久用户ACL。

## 维护入口

部署配置与重建步骤见 `deerflow-deploy/extensions/README.md`。运行测试：

```bash
docker exec chatbot-deerflow-gateway-1 /app/backend/.venv/bin/python /opt/local-extensions/test_pdf_citations.py
```

完整证据目录：`reports/evidence/deerflow-citations/`。最终 Git 检查记录于 `verification-summary.json`，两个上游均为空工作区改动。
