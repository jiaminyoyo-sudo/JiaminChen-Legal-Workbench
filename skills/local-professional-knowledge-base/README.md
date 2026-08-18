# local-professional-knowledge-base

版本：**v0.1.2**

`local-professional-knowledge-base` 用于为法规、案例、实务文章、书籍和其他专业资料建立本地文件型知识库。它处理的是“原始材料 → Markdown 镜像 → 材料索引/地图 → 跨材料关系”，不建立 Wiki 页面，也不默认引入 MCP、BM25 或向量数据库。

适用场景：

- 冷启动一个可检索、可溯源的专业材料库；
- 用户新增材料后做一次增量更新；
- 用 SHA-256 识别新增、变更、重命名和移除；
- 对候选旧材料做比较队列，只有阅读确认后才记录修订、废止、引用或冲突关系。

本 Skill 不替代法规核验、案例研判或正式法律意见。Markdown 镜像只是检索层；引用时必须回链原件，并标明 OCR 或来源不确定性。

## 安装

将本目录整体复制到 `~/.codex/skills/local-professional-knowledge-base/` 或 `~/.claude/skills/local-professional-knowledge-base/`。脚本使用 Python 3 标准库，无额外包依赖。

```bash
python3 scripts/knowledge_base.py init "<项目根目录>"
# 用户把材料放入 原始材料/ 后
python3 scripts/knowledge_base.py update "<项目根目录>" --process
python3 scripts/knowledge_base.py validate "<项目根目录>"
```

`--process` 会复制文本文件、原生提取 XLSX，并把 PDF、Word、PPT 和图片路由到已安装的 `mineru-ocr`。MinerU Token 只能保存在本机 MinerU Skill 配置中，不得写入本项目、索引或答复。

模拟目录见 [`examples/`](examples/)。

Skill 说明、方法文档和示例采用 **CC BY-NC 4.0**；独立脚本和 Agent 配置采用 **MIT License**。具体范围见 [`LICENSE.md`](LICENSE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
