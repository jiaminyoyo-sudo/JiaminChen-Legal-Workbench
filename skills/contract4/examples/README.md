# contract4 模拟示例

本目录全部为从零构造的模拟材料，不对应任何真实客户或事项。

- `模拟技术服务合同.docx`：简化的模拟输入合同；
- `operations.sample.json`：两项局部修订操作；
- `模拟技术服务合同_修订示例.docx`：使用公开版 `scripts/precise_revision.py` 生成的原生 Word 修订稿，修订作者为 `lawyer`。

复现命令：

```bash
python3 ../scripts/precise_revision.py \
  模拟技术服务合同.docx operations.sample.json \
  --author lawyer \
  --start-time 2026-07-22T10:00:00+08:00 \
  --output 模拟技术服务合同_修订示例.docx \
  --print-summary
```

该示例只验证小粒度 Word 修订工程，不代表对任何具体交易的法律意见。
