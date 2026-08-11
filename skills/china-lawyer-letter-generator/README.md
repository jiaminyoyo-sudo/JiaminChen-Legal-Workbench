# china-lawyer-letter-generator

版本：**v0.1.0**

该项目用于在中国法律语境下，从法律关系、签发目的、证据边界、可能抗辩和律师策略出发，形成供律师复核和签发的律师函，并对结构、形式要件、DOCX 和版式进行检查。

主要覆盖履约催告、付款催收、违约通知、解除或终止通知、侵权制止、知识产权警告、劳动人事、公司治理及权利保留等场景。

律师仍负责确认事实、证据、请求强度、两名经办律师、编号、日期、附件、盖章和是否发送。本项目不会自动签名、盖章、寄送或向第三方发送函件。

## 安装与依赖

将本目录整体复制到 `~/.codex/skills/china-lawyer-letter-generator/` 或 `~/.claude/skills/china-lawyer-letter-generator/`。DOCX 构建依赖 Python 3 和 `python-docx`；逐页渲染还需要本机可用的 LibreOffice。先运行：

```bash
python -m pip install python-docx
python scripts/validate_matter.py examples/matter.sample.json
```

模拟输入和已经审计、渲染的输出见 [`examples/`](examples/)。正式使用前须按 `SKILL.md` 完成事实、证据、法律依据、编号、两名律师、日期、附件、盖章和送达复核。

## 信头与授权边界

大成成都信头模板已经确认可以随公开副本上传。大成名称、Logo、信头和其他品牌标识不因项目许可证而当然授予公众身份或品牌使用权；无权使用相应律所身份的使用者应替换为本人或所属机构有权使用的模板，不得暗示不存在的律师、律所或客户关系。详见 [`NOTICE.md`](NOTICE.md)。

Skill 说明、方法文档和示例采用 **CC BY-NC 4.0**；独立脚本和 Agent 配置采用 **MIT License**。许可证不覆盖律所名称、Logo、信头及其他品牌身份权益。具体范围见 [`LICENSE.md`](LICENSE.md) 和 [`NOTICE.md`](NOTICE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
