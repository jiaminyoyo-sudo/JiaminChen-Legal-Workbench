# legal-client-wiki

版本：**v0.1.2**

`legal-client-wiki` 用于单个常年法律服务客户 Wiki 的新建、历史冷启动、规则升级、跨事项专项编译和结构审计。它编译的是经律师确认的客户特有认知，不是法规、案例或文章镜像库。

本 Skill 先按工作模式分流：

- 没有 Wiki 或只有零散旧页面：冷启动；
- 已有 Wiki 且律师明确进入收尾：按收尾闸门准备回写；
- 规则、目录、来源或当前/历史口径需要重构：规则升级；
- 跨事项批量补录或结构审计：运行只读审计脚本。

项目已经建立完整的 `wiki/规则.md` 后，单个事项的日常增量编译直接按项目规则执行，不再把本 Skill 当作运行手册。

公开安装名统一为 `legal-client-wiki`。本目录只提供方法和模拟示例，不公开真实客户 Wiki、事项档案、合同、对话或客户身份信息。

## 安装

将本目录整体复制到 `~/.codex/skills/legal-client-wiki/` 或 `~/.claude/skills/legal-client-wiki/`。结构审计脚本使用 Python 3 标准库，无额外包依赖：

```bash
python3 scripts/audit_wiki.py check <项目>/wiki
python3 scripts/audit_wiki.py report <项目>/wiki --format markdown
```

首次使用时应让 Agent 先读取客户项目的 `AGENTS.md` 和真实材料边界，再在客户目录内建立 Wiki；不要把客户材料复制回本 Skill。

模拟编译结果见 [`examples/模拟客户Wiki编译示例.md`](examples/模拟客户Wiki编译示例.md)。

本目录采用 **CC BY-NC 4.0**。具体范围见 [`LICENSE.md`](LICENSE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
