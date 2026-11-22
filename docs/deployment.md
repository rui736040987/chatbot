# 部署与迁移

## 1. 环境与初始化

要求：Linux 或 WSL2 Linux，Docker Engine + Compose v2、Git、curl、Python 3.11/3.12 及 venv。建议为模型缓存、数据库、千页 PDF 和容器预留充足内存/磁盘。首次初始化需访问 GitHub、容器仓库和模型下载源。

```bash
git clone --recurse-submodules https://github.com/rui736040987/chatbot.git
cd chatbot
./scripts/setup.sh
```

私有仓库需要 GitHub 凭据；也可使用 SSH 克隆。初始化不会覆盖已有配置，生成随机内部密钥、空 PDF 目录和不绑定真实用户的知识库配置。新环境需要下列设置后才能问答：

1. `weknora/.local/secrets/opencode-go.key`：填写 OpenCode Go API key（仅密钥文本）。
2. `.local/deerflow-runtime/runtime.env`：填写同一个 `OPENCODE_GO_API_KEY`。`WEKNORA_API_KEY` 后续创建。
3. `weknora/.local/weknora.env`：将 `WEKNORA_BOOTSTRAP_SYSTEM_ADMIN_EMAIL` 改成准备注册的邮箱。
4. 若模型已不可用，修改 `deerflow-deploy/config.yaml` 的模型名，并在 WeKnora 模型管理同步修改。模板保留现有部署用的 `deepseek-v4.1-flash`，不是对未来服务可用性的保证。

`setup.sh` 会安装本机辅助服务依赖并下载 BGE Small 中文向量模型。模型网关随后使用本地缓存，不依赖原电脑的 OpenCode 配置文件。

```bash
./scripts/start.sh
./scripts/status.sh
```

首次启动可打开两个页面，但此时尚无资料，知识库连接仍是占位配置。

## 2. 首次账号与资料入库

- WeKnora：打开 http://localhost:18088 注册上一步指定的邮箱。
- DeerFlow：首次管理员凭据由系统生成，保存在容器 `/app/backend/.deer-flow/admin_initial_credentials.txt`；在本机私下查看并登录，完成首次账号设置。不要把该文件提交 Git。

```bash
docker compose -f deerflow-deploy/compose.yaml exec gateway cat /app/backend/.deer-flow/admin_initial_credentials.txt
```

两套系统各自保存用户，不共享用户表或密码。仓库不预置原电脑账号。

### 手工入库（推荐）

在 WeKnora 添加模型：

| 用途 | 模型 | OpenAI 兼容地址 | API key |
|---|---|---|---|
| 对话/视觉 | `deepseek-v4.1-flash` | `http://host.docker.internal:18083/v1` | `local-gateway` |
| embedding | `BAAI/bge-small-zh-v1.5`，512 维 | 同上 | `local-gateway` |

模型网关的实际 Go key 来自私有文件；`local-gateway` 是内部占位值。新建文档知识库并选择这些模型，上传 PDF，等待解析、索引完成。需要 Wiki 时在该知识库启用 Wiki 并生成；需要图片解析时配置视觉模型及多模态解析开关。当前使用 WeKnora 原生 docreader；未集成 MinerU。无需启用遗留的宿主 HTTP PDF 解析器，后者仅供旧实验兼容。

下载原来的 10 份手册：

```bash
weknora/.local/venv/bin/python weknora/scripts/download_datasheets.py
```

清单包含原始 URL 和 SHA256；来源失效或文件变更会报错，不会默默接受不同版本。1749 页 RM0090 不包含在这份 10 篇清单里，需要另行提供或迁移原件。

可选自动化：`weknora/scripts/bootstrap_knowledge.py` 会创建默认账户、模型及主知识库，并上传清单。使用它前在 `weknora/.local/login.json` 写入自己的 `username/email/password`（与 bootstrap admin email 一致，权限 600）。它沿用历史实验的 chunk/多模态设置（多模态关闭），不自动生成 Wiki、不创建 DeerFlow Agent，也不导入 RM0090。手工入库后不要未经核对再运行，避免重复创建资料库。

## 3. 连接 DeerFlow 与 WeKnora

1. 在 WeKnora 创建只读检索 API key，将其写入 `.local/deerflow-runtime/runtime.env` 的 `WEKNORA_API_KEY`。
2. 取得 WeKnora 租户 ID、知识库 UUID，以及 DeerFlow 当前登录用户的真实 UUID（登录后 `/api/v1/auth/me` 返回的 `id`；浏览器开发者工具 Network 可查看）。
3. 编辑 `deerflow-deploy/config.yaml` → `plugins[0].config.spaces[0]`，填写 `tenant_id`、`user_ids`、`knowledge_base_ids`。`user_ids` 不是邮箱。默认占位用户不会授权任何真实用户访问。
4. 在 WeKnora 配置 MCP 端点，授权所需知识库并选择只读工具：`list_knowledge_bases`、`list_documents`、`search_knowledge`、`grep_chunks`、`read_document`、`wiki_index`、`wiki_search`、`wiki_read_page`。
5. 在 DeerFlow 设置界面添加 HTTP MCP 连接。容器内地址应为 `http://chatbot-weknora-app-1:8080/mcp/<端点ID>`，Authorization 按 WeKnora 生成的凭据填写。也可编辑 `.local/deerflow-runtime/extensions_config.json`，格式参考 `deploy/mcp.example.json`。
6. 创建名为 `chip-docs` 的智能体，启用 knowledge、文件读取工具组及上述只读 MCP；在聊天中选择目标知识库。需要看上传图片时启用原生 `view_image` 并选择视觉模型。历史命名的其他智能体不会随代码自动出现。

```bash
docker compose -f deerflow-deploy/compose.yaml up -d --force-recreate gateway frontend nginx
```

原生知识 Provider 提供目录选择和来源卡片；MCP 提供连续正文阅读和 Wiki 等工具，两者互补。新环境尚未配置 rerank 模型，WeKnora 某些原生智能体会要求额外配置 rerank/对话模型，不应把该错误归因于资料未入库。

## 4. 原 PDF 页码引用

先完成 WeKnora 入库，再创建 `.local/pdf-sources.json`，格式见 `deploy/pdf-sources.example.json`。每条写入实际文档 ID、知识库 ID、原始 PDF 路径。必须使用入库时的同一份原文件；不要使用重新打印或不同修订版。

```bash
weknora/.local/venv/bin/python deerflow-deploy/build_pdf_catalog.py
# 配置和索引在启动时读取，构建后重启
 docker compose -f deerflow-deploy/compose.yaml restart gateway
```

空目录也能启动，但没有本地 PDF 的文档不能得到本扩展的 PDF 跳转。Wiki 使用原生 chunk/source locator 关联证据；原文件哈希不一致时不强行生成页码。页码是从 1 开始的 PDF 物理页，不是印刷页码。没有 Wiki 的手册仍走原文检索。

## 5. 远程访问

默认仅监听服务器本机 `127.0.0.1:2026/18088`。可用 SSH 隧道保留 localhost 地址：

```bash
ssh -L 2026:127.0.0.1:2026 -L 18088:127.0.0.1:18088 user@server
```

如果通过域名访问，需要配置反向代理、上游可信来源/代理等设置，并修改 runtime.env 中 `DEERFLOW_PUBLIC_URL` 和 `WEKNORA_PUBLIC_URL`。这两个变量只影响引用链接，不能代替反向代理和登录配置。修改环境变量后执行 `up -d --force-recreate gateway`。

宿主模型网关仅绑定 loopback 和 Docker bridge；不对公网开放。

## 迁移现有资料和会话

GitHub 只传代码。要保留已有 Wiki、用户、聊天、知识库 ID 和页码映射，需要另外私下迁移：

- Docker 卷 `chatbot-weknora_app-data`：SQLite 数据库和原始资料。
- `.local/deerflow-runtime/`：用户、会话、配置、MCP、原 PDF 索引与文件。
- `weknora/.local/` 中的配置与密钥（尤其 `SYSTEM_AES_KEY`，丢失可能导致数据库内已加密密钥无法解密）。虚拟环境不可跨机器复制，模型缓存可选复制。
- `weknora/datasheets/` 原件/运行清单、`.local/pdf-sources.json`、`deerflow-deploy/config.yaml`。
- Docker 卷 `chatbot-deerflow_redis-data`（如需保留其持久数据）；临时 docreader 卷通常可重建。

迁移前停服务，以免复制运行中的 SQLite/WAL 获得不一致快照；使用 Docker 卷备份方法导出卷，文件目录使用能保留权限的归档工具。备份包含凭据，应私下传输，不能上传本仓库。目标环境先执行 setup，停服务后还原备份，再启动；不要覆盖备份中的 AES/JWT/会话密钥。保持 Compose 项目名不变，避免创建新空卷。更换主机后核对模型网关 Docker bridge 与域名。

## 验证边界

本次交付检查：模板生成、Compose 渲染、脚本语法、索引构建与本地引用扩展回归。原电脑已经完成过芯片参数/图像/跨章节实验，见 reports；没有在目标机器运行过完整部署。新环境完成账号、知识库绑定后，请用参数、电路图、时序图和跨章节问题逐项复验，并点击 Wiki/PDF 引用。

`deerflow-deploy/extensions/test_pdf_citations.py` 是历史数据集集成测试，依赖原有 UUID、RM0090 和已运行服务；干净环境不能直接运行，需迁移原数据或适配为自己的测试资料。
