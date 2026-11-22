> 2026-11-01 后续进展：新增独立本地扩展后，引用卡片到原始 PDF 物理页的跳转已实测。此文保留当时未实现页定位的历史结果；当前实现性质、补查轮次及限制见 [引用定位复验](deerflow-citation-validation.md)。

# DeerFlow WSL Docker 与芯片知识问答网页验收

验证日期：2026-11-01，Asia/Shanghai。本轮在真实DeerFlow网页中完成发送问题、上传图片、调用工具、查看答案和检查引用，不再只是上一轮的Provider加单轮模型探针。

## 1. 结果与使用入口

DeerFlow已在WSL Linux Docker Engine运行，入口为 http://localhost:2026/workspace/agents 。原WeKnora继续在 http://localhost:18088 运行。两套服务分别持久化，DeerFlow通过API复用现有知识库，没有复制数据库或重新导入手册。

DeerFlow原生账号：`admin@example.com`。密码见本机 `.local/deerflow-runtime/login.json`，也在本次交付消息中提供；未使用免登录模式。

目前有两个原生自定义助手：

| 助手 | 用途 | 配置 |
| --- | --- | --- |
| 芯片手册图文研读助手 `chip-docs` | 参数、检索、跨章节取证 | 知识Provider、WeKnora只读MCP、文件阅读、Go模型 |
| 芯片原图核验助手 `chip-vision` | 上传电路/时序原图核验 | 原生view_image、文件阅读、Go视觉模型；不加载知识检索/MCP |

四类核心问题均完成了网页验证。参数和千页跨章节问题得到正确核心结论；电路及时序初答有额外错误或误读，重新查看原图后得到更正。**不能将这些结果归纳为“所有图片首次回答都准确”。** MCP来源到PDF定位的交互尚未通过。

## 2. 运行与代码边界

Compose配置及启停说明位于 `deerflow-deploy/`：

```bash
cd /home/caorui/workspace/xfusion/chatbot/deerflow-deploy
./start.sh
./stop.sh
```

所有运行服务均在WSL Docker中：Gateway、Next.js前端、Nginx、Redis。主机浏览器自动化只用于验收，未把服务运行在Windows Docker Desktop。Docker Engine数据目录为`/var/lib/docker`。

官方镜像固定为：

| 服务 | 固定摘要 |
| --- | --- |
| backend | `sha256:a23b1a9da4aec585a8ad007bf6d15691ae57aca0d34d74393bc26513866f26fa` |
| frontend | `sha256:88b8e06665db365c4dc4117c2b68eaef5de3bf2f9b47a669212cf57baf242ce9` |
| nginx 1.31.2-alpine | `sha256:54f2a904c251d5a34adf545a72d32515a15e08418dae0266e23be2e18c66fefa` |

两个DeerFlow官方镜像的OCI源码revision均为`a9bd03ef572a4898ea1ba977e906408dc2f28d7d`，构建日期2026-10-31。研究检出的DeerFlow源码仍为`35656d6a9fe2ac76ddcf40335ede7361504ddf5b`；二者不混称同一提交。WeKnora扩展使用研究检出中的原有包，以只读目录挂载至容器，由原生`plugins.use`加载。

本轮调整Compose、环境变量、原生模型配置、助手配置和连接凭据；没有修改WeKnora或DeerFlow上游业务代码，也没有为通过测试更改检索/视觉工具实现。镜像下载的大文件层经过SHA-256校验后导入WSL Docker内容存储。

## 3. 知识库和模型接入

资料范围仍是两个库、11份PDF：10份嘉立创芯片手册，加1份1749页STM32 RM0090。先前提取的77张图片继续由WeKnora管理，不另计成77份文档。网页测试上传的图片属于DeerFlow会话附件，不重复写入WeKnora知识库。

接入分为两条已有路径：

1. **知识Provider**：上游`deerflow-extension-weknora`提供知识库/文档目录、限定范围检索和共享来源证据，支持网页知识范围选择及普通来源卡片。
2. **原生MCP阅读**：运行中的WeKnora发布只读端点，提供`list_knowledge_bases`、`list_documents`、`search_knowledge`、`grep_chunks`、`read_document`。DeerFlow据此按关键词定位并连续阅读章节。

没有启用WeKnora的MCP `ask`工具，因此本轮并非将整道问题委派给WeKnora助手作答。实际规划、工具选择、证据组织和答案生成都发生在DeerFlow Agent中，Go模型由DeerFlow直接调用。

Provider使用专用的`retrieve`凭据，允许范围为两组资料。MCP端点也只允许这两组库和五个只读工具，没有入库、修改或删除权限。网页的Provider范围选择与独立MCP连接权限是不同约束；本轮千页任务的MCP请求实际指向RM0090，不能把网页选择器视作自动改写任意MCP权限。

两种模型配置使用同一个OpenCode Go `deepseek-v4.1-flash`：

- `opencode-go-vision`：原生OpenAI兼容客户端，关闭thinking，用于快速视觉问答。
- `opencode-go-reasoning`：上游已有`PatchedChatDeepSeek`，保留推理历史，启用thinking；声明Go实际支持的low/high/max档位，将通用medium/minimal映射为low。

视觉能力来自前轮Go现场元数据和真实携图调用，而非按其它DeepSeek型号的默认注释推断。本轮Gateway实际SDK调用成功；网页状态中也记录了view_image成功及后续模型输出。

## 4. 网页测试结果

### 4.1 参数问答

[打开参数对话](http://localhost:2026/workspace/agents/chip-docs/chats/388b07e6-fa1d-4527-a426-64b379b36e71)

问题：CH340C是否需要外部晶振；5V和3.3V供电时V3如何连接。

结果正确：CH340C内置时钟；5V供电时V3接0.1μF退耦电容；3.3V供电时V3与VCC相连。实际执行了`knowledge_search`及MCP知识库目录工具，网页显示三个共享来源。点击来源标签可查看真实标题、提供方、知识库名称和检索摘录。初轮页面耗时约10秒。

证据：`parameters-state.json`、`parameters-browser.txt`、`parameters.png`、`parameters-source.png`。来源卡片提供摘录，不等于已经实现PDF页内定位。

### 4.2 电路图

[打开电路对话及C29更正](http://localhost:2026/workspace/agents/chip-vision/chats/05d742b4-736e-41eb-b96b-7c92611d1efc)

使用CH340C.pdf第7页的7.2节电路，另从原PDF提取其原始嵌入图复核。

| 核对项 | 网页实际结果 |
| --- | --- |
| U4、U5 | CH340G、MAX232，正确区分文件名和图面型号 |
| X4 | 12MHz |
| C21/C22 | 各33pF |
| C25～C28 | 各0.47μF |
| 发送链路 | U4 TXD pin2 → U5 T1I pin11 → T1O pin14 → DB9 pin3 |
| 接收链路 | DB9 pin2 → U5 R1I pin13 → R1O pin12 → U4 RXD pin3 |
| C29及去耦 | 初答额外说明错误；再次上传原始小图核验后，更正为C29=0.47μF、VCC到GND，是U5电源去耦电容 |

该轮确实调用原生`view_image`，没有靠知识库caption替代原图。初答约11秒完成，正确回答所问核心项，但额外把C29归到VCC/V+、声称未画U5电源去耦，均不正确。后续定向复核明确纠正了这两条说明，原答案保留。

此外，更早在综合研读助手中做的首轮图像测试，虽然view_image成功，却继续反复阅读整本手册，已手动停止并保留记录。因此配置增加了原图核验助手，仅开放图像/文件阅读工具，避免只读图任务误入全文研读。

证据：`circuit-state.json`、`circuit.png`、`circuit-recheck.png`、`circuit-browser.txt`及`circuit-initial-stopped-state.json`。

### 4.3 时序图

[打开时序初答与原图复核](http://localhost:2026/workspace/agents/chip-vision/chats/c03124fd-8669-46b8-b977-40511b00ab7b)

样本为W25Q32JVSSIQ.pdf的Figure16 Fast Read图，PDF第29页、印刷页28。

| 核对项 | 最终复核结果 |
| --- | --- |
| 指令 | 0Bh，CLK0～7 |
| 地址 | 24位，CLK8～31 |
| dummy | 8个，CLK32～39 |
| 首数据字节 | CLK40～47，bit7先出 |
| dummy期间DO | 图示High Impedance |
| /CS上下行 | 同一次低有效事务，CLK31为折行衔接，不是重新片选 |

初次快速视觉回答正确读出多数参数，却错误宣称图面有/CS重新片选。随后切换到同一Go模型的推理配置，再次上传同一原图，要求复核边沿与CLK31/32衔接。模型再次执行view_image，明确承认原判断错误，并正确解释续行及CLK40～47。没有在复核问题里直接提供正确答案。

因此，此项是**复核后关键事实正确，首答可靠性不足**。图示高阻和正文don't-care也不能被当作通用电气等价关系。

证据：`timing-initial-state.json`、`timing-state.json`、`timing-initial.png`、`timing-recheck.png`、`timing-browser.txt`。

### 4.4 千页跨章节

[打开RM0090跨章节对话](http://localhost:2026/workspace/agents/chip-docs/chats/6aa385b2-ee56-4a10-b71b-3e9ab373287c)

使用与原WeKnora研读验证相同的问题：查证SDIO使用哪个DMA控制器，以及SDIO_DCTRL.DMAEN的位号和含义，分别阅读DMA请求映射与SDIO寄存器章节。

网页选择RM0090知识库，未上传整本手册作为聊天附件。DeerFlow实际执行了12次工具调用，包括目录、检索、关键词查找、read_document及读取外置工具结果的read_file；页面显示约2分3秒。

答案核心事实正确：

- SDIO使用DMA2，Channel4，可选Stream3或Stream6。
- DMAEN为SDIO_DCTRL的bit3，0禁用DMA、1启用DMA。
- 工具历史确实读到了DMA映射表的目标行、SDIO操作流程及DMAEN定义，不是仅引用目录。

相较上一轮仅Provider单轮探针回答“证据不足”，本轮通过MCP连续阅读补齐了章节证据。仍未启用FTS5或更换embedding；语义检索/grep初期有无关结果，真正补齐证据的是文档关键词阅读和窗口化补读。

**引用需要单独评价**：初答把映射表的第一处引用指向只有Table43表头的邻块，实际目标行在后续分块；模型虽然读到正确行，引用落点仍不够准确。另两处操作流程/寄存器定义能够对照原分块。网页复核已更正目标行的原始chunk_id为`752c5a0d-989c-48e1-b7df-3d5aa6c0aa0c`，与前轮人工基准一致。

**页码推断也有误**：直接用pypdfium2读取原始PDF确认，Table43及目标行在第308页，DMAEN定义在第1066页。模型把相邻分块混入的下一页页眉309/1067误当作目标内容的页码，复核时还误把章节范围标记338解释成PDF页码。已在网页要求撤回这些未经定位的页码，仅保留真实分块ID；不能把页码推断计为成功。

更重要的是，初答引用使用原始chunk锚点，点击会打开另一聊天锚点页面，不能打开PDF或高亮原文。故本项结论为：**跨章节核心答案与取证通过，原生PDF引用导航未通过**。不能把文本链接看起来可点击等同完整溯源体验。

证据：`large-state.json`、`large-browser.txt`、`large.png`、`large-source-check.json`。初次三处chunk均存在于WeKnora，跨度分别落在308、1033～1034、1066～1067页，但分块跨页不代表目标事实位于跨度最后一页。第一处表头引用和页码误读均保留。原始PDF直接核验见`large-original-pdf-page-audit.json`。

## 5. 失败和追加实验

除四类核心案例，还保留以下轮次，均不计作额外成功样本：

| 轮次 | 观察与处理 |
| --- | --- |
| 综合助手首次电路题 | 多次无效/冗余阅读，已从网页停止，运行状态interrupted |
| 无knowledge工具的视觉助手设置disabled知识scope | 原生入口返回422；将该助手scope配置留空后正常运行，未改校验代码 |
| 推理模式的扩展电容连接复核 | 触及4096输出上限，返回未完成提示；执行层状态虽为success，答案仍不完整 |
| 新会话追加时序推理复测 | 长时间未完成，页面出现供应端暂时失败及重试提示，已手动停止，状态interrupted |

原图核验助手的预算已提高至16384，模型profile也声明了真实推理档位。配置提高预算不构成所有复杂图像都稳定正确的证据。实际Go调用仍可能慢、失败或误读；本轮未修改上游客户端、工具或模型返回内容来规避这些结果。

四类核心对话与追加实验在 `verification-summary.json` 中分开记录。成功状态只说明运行结束，不等于事实正确、答案完整或引用可用。

## 6. 对原方案分析的更新

上一轮认为千页问题需要补充连续阅读。本轮确认：**当前运行的WeKnora已提供原生MCP文档阅读，接入DeerFlow即可使用，无需为本案例编写新的阅读工具。** 这部分比仅使用只读知识Provider更完整。

图片路径也通过原生view_image运行，上传图可直接进入视觉模型。但“文字查询后自动读取知识库原图”的桥接本轮没有实现；图片测试由网页上传原图完成。入库caption/OCR继续可供普通检索，但不是每次问答都自动把原图送进模型。

目前仍存在的实际差距：MCP文档阅读证据与DeerFlow共享来源卡片没有完整统一，PDF定位缺失；图片首答不稳定；部分推理请求出现输出限制或供应端延迟。当前部署可以用于交互式手册取证与原图复核，不能当作自动电气验证器。

## 7. 证据与复查

所有本轮证据位于 `reports/evidence/deerflow-web/`：

- `backend-image.json`、`frontend-image.json`：镜像摘要、OCI revision及分层信息。
- `native-mcp-tools.json`：运行实例实际暴露的工具和参数。
- `agent-config.json`、`vision-agent-config.json`：原生助手配置。
- `test-cases.json`：原始测试问题和图片。
- `sessions.json`：核心案例与失败实验的对话ID。
- `verification-summary.json`：工具调用、答案、运行状态与结果边界。
- `*-state.json`：原生检查点与消息记录；截图用于证明网页实际展示。

密钥仅保留在私有运行目录和服务环境中，报告、截图及公开证据不包含Go或WeKnora连接密钥。最终服务状态和上游源码检查另存`final-deployment-check.json`。
