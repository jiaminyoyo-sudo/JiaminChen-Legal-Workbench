# case-research

版本：**v0.1.4**

`case-research` 用于中国司法案例检索、事项内全文 JSON 归档、案例表整理，以及从实务文章倒查案例。它强调先查本地归档、再做新检索；正式引用前必须保存完整裁判全文，不能用法宝摘要或文章转述代替原文。

重点覆盖：

- 当前事项 `case-json/` 归档，不向中央库复制全文；
- 法宝/华语原典/法院来源的全文补齐和完整性校验；
- 法答网、法院公号和实务文章的线索留痕与倒查；
- 不含“参考权重”字段的可复核案例表。

参考工作簿只演示复杂专题表的组织方式，其中案例摘录来自公开裁判，不对应本仓库的真实客户事项。

## 安装

将本目录整体复制到 `~/.codex/skills/case-research/` 或 `~/.claude/skills/case-research/`。脚本使用 Python 3 标准库，无额外包依赖。

```bash
python3 scripts/case_matter.py init --matter-root /tmp/模拟事项 --matter-name 模拟咨询
python3 scripts/case_json_lint.py examples/模拟案例.json
python3 scripts/case_table_from_json.py examples/模拟案例.json
python3 scripts/search_case_json.py 模拟 --root examples
```

模拟 JSON 见 [`examples/`](examples/)。正式检索仍需接入法宝、华语原典或法院来源，本目录不提供数据库账号。

Skill 说明、方法文档和示例采用 **CC BY-NC 4.0**；独立脚本和 Agent 配置采用 **MIT License**。具体范围见 [`LICENSE.md`](LICENSE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
