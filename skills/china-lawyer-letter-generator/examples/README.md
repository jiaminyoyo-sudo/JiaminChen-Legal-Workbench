# 中国律师函示例

本目录包含两类用途不同的材料：

- `股东知情权与交易核实_律师函_公开脱敏示例.docx`：代表性律师函成果。保留股东知情权、交易核实、证据保存和克制措辞的专业结构；主体商号统一重构为 A、B、C，自然人改为“甲某”，投资金额、持股比例、交易金额和连续日期一并改写，并清理隐藏元数据和本机路径。正文已标注“公开脱敏示例”。
- `matter.sample.json`：从零构造的付款催收事项，用于运行字段校验和 DOCX 构建脚本；它不是上述代表性律师函的原始事项数据。

运行付款催收模拟输入：

```bash
python3 ../scripts/validate_matter.py matter.sample.json
python3 ../scripts/build_letter_docx.py \
  --input matter.sample.json \
  --template ../assets/大成成都信头纸模板.docx \
  --output /tmp/模拟付款催收_律师函_运行结果.docx
python3 ../scripts/audit_letter_docx.py \
  /tmp/模拟付款催收_律师函_运行结果.docx \
  --template ../assets/大成成都信头纸模板.docx
```

审计代表性示例：

```bash
python3 ../scripts/audit_letter_docx.py \
  股东知情权与交易核实_律师函_公开脱敏示例.docx
```

所有示例只用于展示结构与工程能力，不构成对任何主体或交易的事实陈述，也不得作为真实函件发送。正式签发前必须由经办律师核对委托、事实、证据、法律依据、编号、请求、期限、两名律师、日期、盖章、骑缝章、附件和送达。
