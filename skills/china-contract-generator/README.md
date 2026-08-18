# china-contract-generator

版本：**v0.1.6**

`china-contract-generator` 用于从业务方案起草或重构中国民商事合同。它先形成起草前提要，供律师确认法律关系、依据和结构，再生成合同 Word 稿。它不用于审查或小幅红线修改既有合同；该类任务应使用 `contract4`。

重点覆盖：

- 先定法律关系和履行闭环，再写合同；
- 正文面向相对方，批注面向客户内部决策；
- 优先调用当前 Agent 的 Word 能力，无等效能力时使用内置轻量脚本；
- 两份脱密示例仅作结构参考，不替代现行法核验。

公开副本的可见修订者和批注作者使用 `lawyer`。

## 安装

将本目录整体复制到 `~/.codex/skills/china-contract-generator/` 或 `~/.claude/skills/china-contract-generator/`。脚本使用 Python 3 标准库，无额外包依赖。

```bash
python3 scripts/build_contract_docx.py examples/模拟技术服务合同.txt /tmp/模拟技术服务合同_20260818.docx --author lawyer
```

Skill 说明、方法文档和示例采用 **CC BY-NC 4.0**；独立脚本和 Agent 配置采用 **MIT License**。具体范围见 [`LICENSE.md`](LICENSE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
