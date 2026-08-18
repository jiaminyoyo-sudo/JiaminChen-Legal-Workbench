# 目录与索引 Schema

## 最小目录

```text
项目根目录/
├─ AGENTS.md
├─ 原始材料/
├─ 材料镜像/
└─ 材料索引/
   ├─ manifest.jsonl
   ├─ summary.json
   ├─ source-map.jsonl
   ├─ 材料地图.md
   ├─ relations.jsonl
   ├─ 待比较.jsonl
   └─ 本次更新.json
```

这不是 Wiki。`材料镜像/` 保持与 `原始材料/` 相同的相对目录，每个镜像以原文件全名加 `.md` 结尾，例如：

```text
原始材料/法规/规定.pdf
材料镜像/法规/规定.pdf.md
```

## `manifest.jsonl`

每行一份材料，主要字段：

| 字段 | 含义 |
|---|---|
| `material_id` | 尽量稳定的材料 ID；内容更新时沿用，重命名且哈希相同时沿用 |
| `title` | 原文件名去扩展名 |
| `source_path` | 原件相对项目根目录路径 |
| `mirror_path` | Markdown 镜像相对项目根目录路径 |
| `sha256` | 当前原件 SHA-256 |
| `mirror_sha256` | 当前镜像 SHA-256；无全文时为空 |
| `file_type` | `pdf`、`office`、`image`、`spreadsheet`、`text` 或 `other` |
| `ingest_mode` | `text_copy`、`xlsx_native`、`mineru`、`placeholder` 或 `pending` |
| `processing_status` | `success`、`pending`、`failed`、`removed` |
| `ocr_quality` | `not_applicable`、`unreviewed`、`failed` |
| `keywords` | 机器抽取的检索提示词，不是专业标签结论 |
| `headings` | Markdown 前若干标题，用于渐进披露 |
| `updated_at` | 索引更新时间 |

`removed` 条目保留在 manifest 中，以维持关系可追溯性；材料地图默认把它们单列，不当作在库全文。

## `source-map.jsonl`

只保留原件与镜像回链所需的最小字段：`material_id`、`source_path`、`mirror_path`、`sha256`、`processing_status`。不要记录 Token、外部上传 URL 或本机 Skill 绝对路径。

## `summary.json`

记录当前总数、有效材料数、移除数、类型分布、处理状态、处理方式、待比较数量和关系数量。数字由脚本从索引重建，不由模型手算。

## 检索层级

1. 材料地图：几十行级别的全局视图。
2. Manifest：材料级元数据筛选。
3. `rg` 命中：段落级召回。
4. Agent 阅读候选片段：语义判断。
5. 原件回看：证据和版式核验。

BM25、FTS、向量库或本地 MCP 将来可以读取同一 manifest 和 Markdown 层建立独立索引，但不得成为原件与镜像映射的唯一保存位置。
