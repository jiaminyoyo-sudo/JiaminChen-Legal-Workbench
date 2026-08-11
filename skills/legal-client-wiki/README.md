# legal-client-wiki

版本：**v0.1.1**

`legal-client-wiki` 用于为单个常年法律服务客户新建、历史冷启动、升级或审计本地中文 Wiki，并在跨事项批量补录、知识体系重构时，从律师已经确认的定稿和对话取舍中提炼可复用客户认知。

重点沉淀：

- 公司发展历程和关键状态变化；
- 主体、产品、业务模式及实际运行方式；
- 创新业务和非标合作中的法律关系；
- 经律师确认的法律边界、条件、例外和执行要求。

本 Skill 负责初始化和结构性维护。项目已经建立完整的 `wiki/规则.md`、`wiki/索引.md`、`wiki/日志.md` 和 `wiki/原材料地图.md` 后，单个事项定稿后的日常增量编译应直接按项目规则执行；只有规则缺失、需要升级、出现结构性冲突，或进行批量补录与专项审计时，才重新使用本 Skill。

该项目只提供编译方法和结构，不公开任何真实客户 Wiki、事项档案、合同、对话或客户身份信息。公开安装名统一为 `legal-client-wiki`。

## 安装

将本目录整体复制到 `~/.codex/skills/legal-client-wiki/` 或 `~/.claude/skills/legal-client-wiki/`。本 Skill 不依赖额外脚本或 Python 包。首次使用时应让 Agent 先读取客户项目的 `AGENTS.md` 和真实材料边界，再在客户目录内建立 Wiki；不要把客户材料复制回本 Skill。成熟项目的日常增量编译以其 `wiki/规则.md` 为唯一运行规则。

模拟编译结果见 [`examples/模拟客户Wiki编译示例.md`](examples/模拟客户Wiki编译示例.md)。

本目录采用 **CC BY-NC 4.0**。具体范围见 [`LICENSE.md`](LICENSE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
