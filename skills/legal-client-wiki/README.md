# legal-client-wiki

版本：**v0.1.0**

`legal-client-wiki` 用于把律师已经确认的定稿、客户反馈、实际执行材料及形成定稿过程中的问题和取舍，编译为可溯源、可复用且不会静默自相矛盾的客户认知。

重点沉淀：

- 公司发展历程和关键状态变化；
- 主体、产品、业务模式及实际运行方式；
- 创新业务和非标合作中的法律关系；
- 经律师确认的法律边界、条件、例外和执行要求。

该项目只提供编译方法和结构，不公开任何真实客户 Wiki、事项档案、合同、对话或客户身份信息。公开安装名统一为 `legal-client-wiki`。

## 安装

将本目录整体复制到 `~/.codex/skills/legal-client-wiki/` 或 `~/.claude/skills/legal-client-wiki/`。本 Skill 不依赖额外脚本或 Python 包。首次使用时应让 Agent 先读取客户项目的 `AGENTS.md` 和真实材料边界，再在客户目录内建立 Wiki；不要把客户材料复制回本 Skill。

模拟编译结果见 [`examples/模拟客户Wiki编译示例.md`](examples/模拟客户Wiki编译示例.md)。

本目录采用 **CC BY-NC 4.0**。具体范围见 [`LICENSE.md`](LICENSE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
