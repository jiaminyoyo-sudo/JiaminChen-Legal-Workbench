# local-professional-knowledge-base 模拟示例

本目录全部为从零构造的模拟材料，不对应任何真实客户、案件或内部档案。

复现：

```bash
python3 ../scripts/knowledge_base.py init .
# 已预置 原始材料/法规/模拟管理办法.txt
python3 ../scripts/knowledge_base.py update . --process
python3 ../scripts/knowledge_base.py validate .
```

预期结果：生成 `材料镜像/`、`材料索引/manifest.jsonl`、`材料地图.md` 和项目 `AGENTS.md` 中的知识库入口块。该示例只验证文件型知识库结构，不构成法律意见。
