# MinerU 集成和保密边界

本 Skill 负责编排，`mineru-ocr` 负责实际 OCR。这样学员在第一节课安装、配置一次 MinerU 后，本 Skill 可以统一完成知识库冷启动和后续更新，同时避免复制 Token、历史归档和真实材料。

## 发现顺序

`knowledge_base.py update --process` 按以下顺序寻找转换脚本：

1. 环境变量 `MINERU_SKILL_PATH` 指向的 Skill 目录；
2. 本 Skill 同级目录中的 `mineru-ocr`；
3. `~/.codex/skills/mineru-ocr`；
4. `~/.claude/skills/mineru-ocr`；
5. 项目内 `.codex/skills/mineru-ocr` 或 `.claude/skills/mineru-ocr`。

找不到时，PDF、Office 和图片记录为 `pending` 或 `failed`，并生成显眼占位；不伪装成全文。

## 调用方式

脚本把单份原件复制到临时目录，再调用：

```bash
/usr/bin/osascript -l JavaScript <mineru-ocr>/scripts/convert.js <临时文件>
```

成功后只把临时目录中的 Markdown 复制到项目 `材料镜像/`。原件不被改写。

## 安全要求

- 调用 MinerU 意味着材料会发送给第三方服务；必须先遵守项目保密、授权和数据出境/服务条款要求。
- Token 只写入已安装 MinerU Skill 的 `config/.env`；不得写入本 Skill、项目、教程、日志、索引或聊天回复。
- 课程包不包含 `.env`、Token、OCR archive、历史结果或真实项目路径。
- OCR 输出未经人工核验时标为 `unreviewed`。页码、表格、印章、脚注和复杂版式需要回看原件。
- MinerU 调用失败时保留错误类型的简短说明，不把完整响应、上传 URL 或认证头写入知识库。
