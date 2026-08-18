# 陈佳敏律师 AI 工作台

**JiaminChen Legal Workbench**

这是陈佳敏律师持续整理的法律 AI Agent、Skills 与确定性工具工作台，关注资本市场及商业法律实务中的真实工作和真实交付。

这里不是提示词合集。每个项目都将围绕明确的法律场景、输入材料、判断边界和交付物设计，并尽量区分：

- 模型进行法律关系、风险和事实语义判断；
- 代码完成 Word 修订、结构校验、索引、溯源和其他确定性工作；
- 外部法条、案例及原始材料提供证据；
- 律师确认事实、商业底线和最终结论。

当前开放项目已完成公开副本整理、许可证标注、模拟示例和本地安装验证。每个 Skill 均可独立下载、安装和使用。

## 首批开放项目

| 项目 | 解决的问题 | 主要交付 | 状态 |
|---|---|---|---|
| [`contract4`](skills/contract4/) | 以最小必要幅度审查和修订中国商事合同，强化不修改闸门、客户口径批注、附件勾稽与责任闭环 | Word 原生修订稿、必要批注及待确认事项 | v0.1.0 |
| [`china-lawyer-letter-generator`](skills/china-lawyer-letter-generator/) | 从法律关系、证据边界和签发目的出发，形成供律师复核的中国律师函 | 经结构与版式检查的 DOCX；签发阶段可配套 PDF | v0.1.0 |
| [`legal-client-wiki`](skills/legal-client-wiki/) | 新建、冷启动、规则升级、跨事项专项编译或结构审计客户 Wiki | 本地客户 Wiki、索引、规则、审计报告与更新记录 | v0.1.2 |
| [`local-professional-knowledge-base`](skills/local-professional-knowledge-base/) | 为法规、案例、文章和专业资料建立可检索、可溯源的本地文件型知识库 | 原始材料目录、Markdown 镜像、材料索引/地图和比较队列 | v0.1.2 |

## 如何选择

- 需要审查或修订商事合同：从 `contract4` 开始；
- 需要形成履约催告、付款催收、违约通知或其他律师函：查看 `china-lawyer-letter-generator`；
- 需要新建、冷启动、规则升级、跨事项专项编译或结构审计常年客户 Wiki：查看 `legal-client-wiki`；成熟 Wiki 的日常增量编译直接遵循项目自己的 `wiki/规则.md`；
- 需要为法规、案例、文章或专业资料建立文件型知识库：查看 `local-professional-knowledge-base`；
- 需要了解多个组件如何组成完整工作链：查看 [`solutions/`](solutions/)；
- 需要先看模拟产出：查看 [`showcase/`](showcase/)。

## 安装

先克隆仓库，再只复制需要的 Skill：

```bash
git clone https://github.com/jiaminyoyo-sudo/JiaminChen-Legal-Workbench.git
mkdir -p ~/.codex/skills
cp -R JiaminChen-Legal-Workbench/skills/contract4 ~/.codex/skills/
```

将最后一行的 `contract4` 替换为 `china-lawyer-letter-generator`、`legal-client-wiki` 或 `local-professional-knowledge-base`，即可独立安装另一个 Skill。Claude Code 用户可复制到 `~/.claude/skills/`。具体依赖、示例和边界见各项目 README。

## 关于陈佳敏

资本市场律师，沉浸式 vibe coding 实践者，关注人工智能如何进入律师的真实工作流。

- 微信视频号：**东圭每**
- 小红书：**陈佳敏律师（AI版）**
- 小红书号：`264629256`
- 个人微信：`Yangyoyo2022`（商业授权）
- 邮箱：`yangyoyo2022@qq.com`（商业授权）

## 许可证与商业授权

本仓库按项目分别授权，不使用一份根许可证覆盖全部内容：

- 通用工具原则上采用 MIT License；
- 核心法律专业 Skills 原则上采用 CC BY-NC 4.0；
- 第三方改造项目保留原作者、原许可证和改造说明；
- 律所信头、Logo、模板及其他品牌资产不因项目许可证而当然获得使用授权。

具体以每个项目目录中的 `LICENSE.md`、README 和 NOTICE 为准。商业使用、企业内部部署、培训或其他授权需求，可通过微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com` 联系。

## 公开与隐私

公开内容不包含真实客户材料、事项档案、内部知识库或密钥。示例使用从零构造的模拟材料，或在保留专业结构的同时重构主体、人物、金额、日期和其他识别组合的公开脱敏材料。`china-lawyer-letter-generator` 所含大成成都信头模板已获上传许可，但其品牌与身份使用权不随项目许可证开放。具体规则见 [`docs/公开与隐私说明.md`](docs/公开与隐私说明.md)；信头和品牌使用边界见 [`NOTICE.md`](NOTICE.md)。

## 使用边界

本项目用于改善律师工作的信息组织、分析和文档交付，不替代律师对事实、证据、现行法律和最终文件的专业复核。使用者应自行核验适用法律、材料真实性、文书内容和签发权限。
