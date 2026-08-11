# contract4

版本：**v0.1.0**

`contract4` 面向中国商事合同审查与修订。它先识别客户立场、真实交易和法律关系，再通过“不修改／仅批注／局部红线／结构性修订”闸门控制修改范围，并检查附件勾稽、程序义务可执行性和违约责任闭环，最终形成原生 Word 修订稿。

本目录包括：

- Skill 说明和合同审查方法；
- 最小修订、客户口径批注及 Word 红线工程规则；
- 带操作范围预检与结构性修订保护的小粒度 Word 修订脚本；
- 完全模拟或充分脱敏的输入、输出示例。

## 安装

将本目录整体复制到 `~/.codex/skills/contract4/` 或 `~/.claude/skills/contract4/`。脚本需要 Python 3 和 `lxml`：

```bash
python3 -m pip install lxml
```

运行模拟修订：

```bash
python3 scripts/precise_revision.py \
  examples/模拟技术服务合同.docx \
  examples/operations.sample.json \
  --output /tmp/模拟技术服务合同_修订结果.docx \
  --author lawyer \
  --check-only
```

预检通过后移除 `--check-only` 即可生成修订稿。示例输出见 [`examples/`](examples/)。脚本适合局部替换、删除和插入；复杂批注、文本框或异常 Office 结构仍应使用专业文档工具并按需渲染复核。

Skill 说明、方法文档和示例采用 **CC BY-NC 4.0**；独立脚本和 Agent 配置采用 **MIT License**。具体范围见 [`LICENSE.md`](LICENSE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
