> 本文记录原部署；在新环境请优先按 [部署说明](../docs/deployment.md) 初始化。原有账号、智能体和资料不随代码复制。

# WeKnora 芯片手册知识库

已在 WSL Ubuntu 内部署，Docker Engine 数据目录为 `/var/lib/docker`。所有容器、PDF、数据库及本地向量模型都在 WSL；未使用 Windows Docker Desktop。

- 网页：<http://localhost:18088>
- 账号：`admin@weknora.local`；密码保存在 `.local/login.json`。
- 知识库：**嘉立创芯片手册（10篇）**。
- 智能体：**芯片手册助手**、**芯片手册研读助手**、**芯片图文问答助手**，已绑定知识库与 OpenCode Go 模型。
- 图片问答已验证：上传电路图/时序图，以及不上传图片、检索已入库图像描述与OCR。详见 [图片问答实测](docs/vision-qa-validation.md)。

进入左侧“智能体”选择“芯片手册助手”即可提问，也可打开左侧已保存的“已验证：CH340C晶振和供电（引用手册）”对话。回答下的文档引用可以打开 PDF 并高亮原文。

## 启停

在 WSL 的本目录运行：

```bash
./start.sh
./stop.sh
```

`start.sh` 启动 WSL 内的 Docker Engine、两个 WSL 本地适配服务和 Compose 容器。它使用 `wsl.exe -u root -- service docker start` 在需要时启动 **Linux Docker 服务**；这不是 Windows Docker Desktop。适配服务通过 WSL init 独立运行，关闭调用终端后仍能使用。

停止操作保留数据库与文档。WSL 关闭后需要重新运行 `./start.sh`。

## 部署内容

- `WeKnora/`：上游 Git 源码，提交 `80e8345903ce4af970497de8359b8b4ea4ce4917`。
- `compose.yaml`：官方 app/UI 镜像，已固定镜像摘要，使用 SQLite 持久化。
- Docker 卷 `chatbot-weknora_app-data`：SQLite 数据库、上传原始 PDF、分块、向量和引用定位。
- `scripts/model_gateway.py`：本地 OpenAI 兼容接口，转发 OpenCode Go 请求并补充其要求的会话标识；向量请求使用 CPU 本地的 `BAAI/bge-small-zh-v1.5`（512维），不使用远程 embedding API。
- 官方 `docreader` 容器：当前实际使用的原生 gRPC 解析服务，支持正文、PDF图片提取及矢量图渲染；`scripts/pdf_reader.py` 是早期轻量适配器，已不作为解析入口。
- `.local/secrets/opencode-go.key`：用户提供的新 Go 密钥；未修改原 OpenCode 配置。
- `.local/weknora.env`：数据库、签名与加密配置；`.local/` 已加入忽略规则。

网页与后端仅映射本机 `18088`、`18081`。本地适配接口使用回环地址及 Docker bridge 地址 `18083`、`18084`。

## 模型与范围

对话及视觉模型为 OpenCode Go 的 `deepseek-v4.1-flash`，通过项目原生模型配置直连 Go，已实测图片输入、鉴权与流式问答。本地 BGE 文本向量继续使用本地服务；模型需要联网。

当前官方 app 镜像的 SQLite 没有编入 FTS5，故使用 **向量语义检索**，关键词全文索引不可用。已启用图片上传、视觉理解、原生图片描述及OCR，并重解析 CH340/W25Q32 两份样本；其它八份仍为文本索引。BGE是文本向量模型，未配置图片embedding和重排模型；未验收整本千页扫描件或Office解析。

## 已导入的 PDF

| 芯片 | 手册来源/厂商 |
| --- | --- |
| CH340C | 嘉立创商城，沁恒 |
| AMS1117-3.3 | 嘉立创商城，AMS1117 手册 |
| TP4056 | 嘉立创商城，锂电充电管理 |
| FT232RL-REEL | 嘉立创商城，FTDI |
| W25Q32JVSSIQ | 嘉立创商城，Winbond |
| NE555DR-UMW | 嘉立创商城，UMW |
| SN74HC595DR | 嘉立创商城，TI |
| LM358-MSK | 嘉立创 PDF，MSKSEMI |
| LM393-ST | 嘉立创 PDF，ST |
| ESP32-C3 | 嘉立创 PDF，Espressif |

`datasheets/manifest.json` 保存每份 PDF 的真实下载地址、SHA-256、大小与导入 ID。不同厂商的同名芯片应以各自手册为准。

```bash
python3 scripts/download_datasheets.py  # 校验，缺失时重新下载
.local/venv/bin/python scripts/check_ingestion.py
```

## 验证证据

10/10 PDF 均已完成解析并启用。实测 CH340C 晶振、5V/3.3V供电问题，获得完整回答和两条有效引用；引用可定位到原始 PDF 页面。

- `evidence/ingestion-status.json`：全部文档处理状态。
- `evidence/retrieval.json`：真实检索内容、得分与 PDF 定位。
- `evidence/CH340C问答.md`、`evidence/verified-qa-stream.txt`：回答及流式事件。
- `evidence/knowledge-base.png`、`evidence/verified-chat.png`、`evidence/citation-preview.png`：网页验收截图。

## 知识问答深入验证（2026-11-01）

已使用现有API启用父子分块并重解析10份手册；新增“芯片手册研读助手”用于跨页/跨章节/跨型号查阅。另有独立的1749页STM32 RM0090验证库及“STM32千页手册研读助手”。

跨页、跨章节和千页实测、图片能力边界，以及快速RAG漏召回英文手册的反例，见 [详细分析](docs/knowledge-qa-analysis.md)。本轮未修改业务代码或适配服务代码。

## 自定义智能体与跨项目分析

- [集成自定义智能体方案](docs/custom-agent-integration.md)：MCP接入及外部执行器适配。
- [DeerFlow知识问答对比](../reports/deerflow-knowledge-qa-analysis.md)：已有WeKnora扩展、实际兼容性与问答限制。

本项目已整体移动至 `chatbot/weknora/`，请在该目录执行启停脚本；网页端口和数据库卷不变。
