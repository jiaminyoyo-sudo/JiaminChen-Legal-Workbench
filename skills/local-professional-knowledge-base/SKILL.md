---
name: local-professional-knowledge-base
description: 为法规、案例、实务文章、书籍及专业资料建立本地文件型知识库。适用于用户要求冷启动或增量更新“原始材料 → Markdown 镜像 → 材料索引/地图 → 跨材料关系”的可检索、可溯源知识库；不建立 Wiki 页面，不启动后台监控，也不默认引入 MCP、BM25 或向量数据库。
---

# 本地专业知识库

建立透明、可迁移的文件型知识库：原件是证据层，Markdown 是检索层，材料索引负责定位和回链，`relations.jsonl` 记录经比较确认的知识演进关系。

## 工作边界

- 不建立 Wiki、主题页、知识页或双链体系。
- 不启动后台监控。用户说“更新知识库”时才运行一次增量更新。
- 不修改、移动、重命名、删除或覆盖 `原始材料/` 中的文件。
- Markdown 镜像不是自动确认的专业结论；引用时回链原件，并标示 OCR 或来源不确定性。
- 第一版使用文件、JSONL、Markdown 和 `rg`。不要把 MCP、BM25、向量数据库设为冷启动前置条件。
- 不把 Token、`.env`、OCR 归档、原始材料或绝对个人路径写入课程包、项目索引或答复。

## 冷启动

1. 确认项目根目录和保密边界。第三方 OCR 不适合处理的材料不得提交 MinerU。
2. 运行：

```bash
python <本Skill目录>/scripts/knowledge_base.py init "<项目根目录>"
```

3. 检查生成的项目 `AGENTS.md`。若项目已有规则，脚本只维护标记块，不覆盖其他内容。
4. 用户把材料放入 `原始材料/` 后，运行：

```bash
python <本Skill目录>/scripts/knowledge_base.py update "<项目根目录>" --process
python <本Skill目录>/scripts/knowledge_base.py validate "<项目根目录>"
```

5. 首次搭建时必须读取 [references/agents-template.md](references/agents-template.md) 和 [references/index-schema.md](references/index-schema.md)，核对项目入口和索引字段。

`--process` 会直接复制文本类文件、原生提取 XLSX，并把 PDF、Word、PPT 和图片路由到已安装的 `mineru-ocr`。如 MinerU 尚未安装或配置，保留失败占位和待处理状态，不得声称已经读取全文。具体路由与隐私边界见 [references/mineru-integration.md](references/mineru-integration.md)。

## 增量更新

用户说“知识库需要更新”“我又放了材料”或同义指令时：

1. 先读项目 `AGENTS.md`。
2. 运行 `update --process`，用 SHA-256 识别新增、内容变更、重命名和移除。
3. 检查 `材料索引/本次更新.json`、`summary.json`、`材料地图.md` 和 `待比较.jsonl`。
4. 对 `待比较.jsonl` 中每个新增/变更材料，只读取它及排序靠前的候选旧材料；候选分数仅用于召回，不代表存在真实关系。
5. 比较法规效力与修订、案例争点与裁判理由、文章立场与适用前提。确认后才更新 `relations.jsonl`；无法确认就不写关系，并记录待人工核验事项。
6. 再运行 `validate`，报告新增、变更、移除、失败、待比较和已确认关系数量。

关系写法和判断边界见 [references/relations-schema.md](references/relations-schema.md)。不要把“相似”“同题”误写成“修订”“冲突”或“取代”。

## 检索与回答

先渐进定位，再读取正文：

```bash
sed -n '1,220p' "<项目根目录>/材料索引/材料地图.md"
rg -n -i "<关键词>" "<项目根目录>/材料索引/manifest.jsonl" "<项目根目录>/材料镜像"
```

检索顺序：

1. `材料地图.md`：了解规模、类型、更新状态和材料入口。
2. `manifest.jsonl`：按标题、路径、关键词、状态和材料 ID 缩小范围。
3. `材料镜像/**/*.md`：关键词检索并只读命中片段。
4. `relations.jsonl`：沿已确认关系扩展到新旧版本、引用、冲突或区分材料。
5. 原件：需要核对版式、页码、印章、图表或 OCR 疑点时回看。

“语义检索”在本架构中首先由 Agent 对候选片段进行语义判断，不等于必须部署向量数据库。只有材料规模和真实查询测试表明 `rg + 索引 + Agent 复核` 召回不足时，才另行评估 BM25/FTS 或向量检索；它们是可替换的检索加速层，不改变原件、镜像和来源映射。

回答必须尽量列出：材料标题、Markdown 镜像相对路径、原件相对路径、可获得的页码/章节、处理状态。对 OCR 失败、占位、版本冲突和未确认关系明确说明。

## 资源

- `scripts/knowledge_base.py`：初始化、增量处理、材料索引/地图、比较队列和校验。
- [references/agents-template.md](references/agents-template.md)：首次生成的项目级入口规则。
- [references/index-schema.md](references/index-schema.md)：目录、索引字段和检索层级。
- [references/relations-schema.md](references/relations-schema.md)：知识迭代比较和关系记录。
- [references/mineru-integration.md](references/mineru-integration.md)：MinerU 安装发现、调用和保密边界。
