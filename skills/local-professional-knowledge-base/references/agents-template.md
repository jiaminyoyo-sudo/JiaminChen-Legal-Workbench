# 项目 AGENTS.md 模板说明

初始化脚本会在项目根目录写入一个受标记管理的规则块。项目已有 `AGENTS.md` 时，只新增或替换该规则块，不覆盖其他项目规则。

规则块必须表达以下约束：

```markdown
<!-- local-professional-knowledge-base:start -->
## 本地专业知识库

本项目采用文件型专业知识库，不采用 Wiki 页面体系。

- 原始材料：`原始材料/`
- Markdown 镜像：`材料镜像/`
- 机器索引：`材料索引/manifest.jsonl`
- 规模摘要：`材料索引/summary.json`
- 人工入口：`材料索引/材料地图.md`
- 原件映射：`材料索引/source-map.jsonl`
- 已确认关系：`材料索引/relations.jsonl`
- 增量比较队列：`材料索引/待比较.jsonl`

### 更新规则

- 用户维护原件；Agent 不修改、移动、重命名、删除或覆盖原件。
- 用户要求“更新知识库”时，调用 `local-professional-knowledge-base` 做一次增量更新，不启动后台监控。
- 文本文件直接生成镜像；PDF、扫描件、图片和复杂 Office 文件路由到已安装的 `mineru-ocr`。
- MinerU Token 只能保存在本机 Skill 配置中，不得写入项目、索引、日志或答复。
- 新增或变更材料处理后，检查待比较队列；只有实际阅读比较后，才记录修订、废止、引用、解释、冲突、区分或补充关系。

### 检索规则

- 先读 `材料索引/材料地图.md` 和 `manifest.jsonl`，再在 `材料镜像/` 中按关键词定位；不得默认一次性读取全部镜像。
- Markdown 是检索镜像，不是自动确认的专业结论。
- 回答尽量给出镜像路径、原件路径和可获得的页码或章节。
- OCR 失败、质量可疑、来源不明或关系未确认时，明确标记并回看原件。
<!-- local-professional-knowledge-base:end -->
```

公开副本不把本机 Skill 绝对路径写入项目。安装后使用本目录中的相对命令，或在项目 AGENTS.md 中自行记录本机安装位置。
