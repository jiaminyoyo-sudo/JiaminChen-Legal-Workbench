# bse-private-placement-investor-opinion 模拟示例

本目录不提供真实事项稿。公开模板本身即为脱敏结构和版式示例。

复现工作副本：

```bash
python3 ../scripts/instantiate_template.py --output /tmp/模拟北交所定增投资方法律意见书_DC_20260818.docx
python3 ../scripts/audit_opinion.py /tmp/模拟北交所定增投资方法律意见书_DC_20260818.docx
```

拟制工作稿允许保留审核注册文件占位和待更新批注；签发稿必须取得文件、填入事实并清除批注后再运行 `--final`。该示例只验证模板复制和审计脚本，不构成法律意见。
