# china-legal-research-memo

版本：**v0.1.6**

`china-legal-research-memo` 用于中国法律专题调研和正式书面备忘录。它先锁定事实和问题，再建立问题树与主张—来源台账，核验现行法和案例，按团队稳定风格形成结论、分析和可执行建议，并用脚本检查结构、引证、占位符和台账完整性。

v0.1.6 新增上市公司信息披露的专门来源路径、不可单独援引的来源清单，以及正文脚注与案例原文文件包的交付规则。

本 Skill 不替代短篇逐问咨询、合同红线、诉讼文书或律师函。正式引用仍须回到法宝、元典或官方原文。

## 安装

将本目录整体复制到 `~/.codex/skills/china-legal-research-memo/` 或 `~/.claude/skills/china-legal-research-memo/`。脚本使用 Python 3 标准库，无额外包依赖。

```bash
python3 scripts/source_ledger_audit.py --write-template examples/模拟主张来源台账.csv
python3 scripts/source_ledger_audit.py examples/模拟主张来源台账.csv
python3 scripts/research_memo_audit.py examples/模拟调研备忘录.md
```

模拟备忘录见 [`examples/`](examples/)。该示例只验证结构和审计脚本，不构成法律意见。

Skill 说明、方法文档和示例采用 **CC BY-NC 4.0**；独立脚本和 Agent 配置采用 **MIT License**。具体范围见 [`LICENSE.md`](LICENSE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
