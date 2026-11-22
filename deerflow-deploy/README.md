> 本文记录原部署；在新环境请优先按 [部署说明](../docs/deployment.md) 初始化。原有账号、智能体和资料不随代码复制。

# DeerFlow WSL Docker 部署

入口：http://localhost:2026/workspace/agents 。使用原生账号登录，账号密码保存在本机 `../.local/deerflow-runtime/login.json`，该文件权限为600。

部署使用WSL Linux Docker Engine。官方前后端镜像固定摘要，原生WeKnora知识Provider以只读目录挂载；新增的本地PDF引用扩展通过现有`plugins`入口加载，复用该Provider。未修改两个上游仓库的代码；引用页定位包含本地扩展代码，并非纯配置。

```bash
cd /home/caorui/workspace/xfusion/chatbot/deerflow-deploy
./start.sh
./stop.sh
```

`start.sh`先确保现有WeKnora运行，再启动DeerFlow。`stop.sh`只停止DeerFlow，不停止WeKnora或删除数据。

## 使用

- **芯片手册图文研读助手**：文档参数、知识库检索、千页跨章节阅读。接入WeKnora原生知识目录和只读MCP阅读工具。
- **芯片原图核验助手**：上传电路图/时序图，使用原生`view_image`直接看图；不配置知识检索或MCP工具。

模型都来自OpenCode Go的`deepseek-v4.1-flash`。提供快速视觉与低强度推理两种配置，推理配置使用上游已有的`PatchedChatDeepSeek`兼容类。原图核验助手输出预算已由4096提高至16384；推理输出、模型延迟和误读仍需核对，不能把一次运行成功等同电气设计正确。

## 数据与连接

- `config.yaml`：模型、工具、知识库Provider和运行配置；密钥通过环境变量引用。
- `../.local/deerflow-runtime/runtime.env`：后端模型/知识库凭据及服务密钥。
- `../.local/deerflow-runtime/frontend.env`：前端所需会话密钥，不包含Go或WeKnora API密钥。
- `../.local/deerflow-runtime/extensions_config.json`：只读MCP连接凭据。
- `../.local/deerflow-runtime/data`：原生用户、会话、上传附件、检查点及数据库。
- Docker卷`chatbot-deerflow_redis-data`：Redis持久数据。
- 外部Docker网络`chatbot-weknora_default`：Gateway通过容器网络访问现有WeKnora，不复制SQLite。

知识库凭据仅有`retrieve`能力，限制两组已授权资料。MCP只提供目录、检索、grep及连续阅读，未开放写入、删除或`ask`工具。DeerFlow使用自己的Agent循环和Go模型回答。

网页只绑定本机2026端口，Gateway/Redis不暴露宿主端口。未挂载Docker socket；LocalSandbox的宿主shell执行关闭。

## 验收边界

参数、图面关键项和千页问题已在网页验证；图片初答有误读，经原图复核纠正。新增本地扩展后，核验过原文的来源卡片可以跳转原始PDF物理页；MCP正文需经`pdf-evidence`精确核验后取得标准引用。未核验来源不强行添加页码。追加实验存在输出上限及上游暂时失败，报告保留这些轮次。

完整过程、已保存的对话和证据见 [网页验收报告](../reports/deerflow-web-validation.md)。

引用实现与重建说明见 [本地扩展](extensions/README.md)，网页复验见 [引用定位报告](../reports/deerflow-citation-validation.md)。
