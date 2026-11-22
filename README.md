# 芯片手册知识问答：DeerFlow + WeKnora

一个总项目管理两套上游、部署配置和独立集成扩展。支持 WeKnora 文档入库/Wiki，以及 DeerFlow 的 Wiki + 原文联合检索和原 PDF 物理页引用。

**新环境请从 [部署说明](docs/deployment.md) 开始。** 本仓库不包含账号密码、API 密钥、数据库、聊天记录、下载的 PDF 或生成的 Wiki；克隆代码不会自动恢复现有知识库。

```bash
git clone --recurse-submodules https://github.com/rui736040987/chatbot.git
cd chatbot
./scripts/setup.sh
# 按 docs/deployment.md 填写生成的私有配置和模型密钥
./scripts/start.sh
```

| 服务 | 本地入口 | 职责 |
|---|---|---|
| WeKnora | http://localhost:18088 | 解析、入库、混合检索、Wiki、原文证据 |
| DeerFlow | http://localhost:2026 | 智能体、多轮阅读、知识问答、工具编排 |

支持 Linux / WSL2 内的 Linux Docker Engine；在 WSL 中执行全部命令。镜像按 digest 固定，两套上游按 Git submodule commit 固定。当前镜像针对现有部署验证过；其他 CPU 架构须检查镜像支持。

## 目录

```text
chatbot/
├── deerflow/                 # 未修改的上游 submodule
├── weknora/
│   ├── WeKnora/              # 未修改的上游 submodule
│   ├── compose.yaml          # WeKnora 部署
│   ├── scripts/              # 模型适配、资料下载/入库、验证
│   └── datasheets/           # 公开资料下载清单；PDF 不入 Git
├── deerflow-deploy/
│   ├── compose.yaml          # DeerFlow 部署
│   ├── config.example.yaml   # 可移植配置模板
│   └── extensions/           # 本项目的 PDF/Wiki 引用扩展
├── deploy/                   # 环境模板、依赖、原 PDF 索引清单示例
├── scripts/                  # 统一初始化、启停、状态检查
├── docs/                     # 新环境部署说明
├── reports/                  # 既有实验报告，不代表新环境已完成验收
└── .local/                  # 私有配置/运行数据，忽略提交
```

保留现有路径是为了兼容当前挂载与脚本；部署和集成层统一纳入根仓库。没有把两套上游源码合并或改写。新增的 PDF 引用是本地扩展代码，不能称为纯配置实现。

## 使用与维护

- `./scripts/status.sh` 查看服务；`./scripts/stop.sh` 停止服务并保留数据。
- 原有资料可按 [数据迁移说明](docs/deployment.md#迁移现有资料和会话) 私下迁移。
- 上游升级先更新 submodule 和对应镜像，再验证扩展 API、登录、入库、Wiki、图片和引用定位；不要直接把镜像换成 `latest`。
- 本地模型配置使用 OpenCode Go；可用模型、视觉能力和套餐权限需在新环境确认。
- 现有报告：[知识问答分析](weknora/docs/knowledge-qa-analysis.md)、[DeerFlow 验收](reports/deerflow-web-validation.md)、[引用定位](reports/deerflow-citation-validation.md)。其中本机会话链接、ID 和实验结果属于历史部署。

## 许可

WeKnora、DeerFlow 及其依赖沿用各自上游许可证，见 submodule 根目录 LICENSE。芯片手册属于各原厂/发布方，仓库仅提供下载地址和校验清单，不重新分发 PDF。
