# bse-private-placement-investor-opinion

版本：**v0.1.3**

`bse-private-placement-investor-opinion` 用于为拟参与北京证券交易所上市公司向特定对象发行股票的投资方起草、复核并交付中国法律意见书。它服务投资方内部决策，不替代发行人申报法律意见书，也不替代发行完成后由上市公司律师出具的专项法律意见书。

重点覆盖：

- 出具目的、拟制时点和材料缺口的区分；
- 投资方主体资格、内部决策、国资审核与系统备案；
- 投资者适当性、竞价认购、签约缴款、新增股份登记、SS/CS 标识和限售；
- 法规原文核验台账、Word 模板实例化和确定性审计。

公开模板已脱敏，主体、金额、文号均为占位符。大成成都信头和品牌使用权不随项目许可证开放。

## 安装

将本目录整体复制到 `~/.codex/skills/bse-private-placement-investor-opinion/` 或 `~/.claude/skills/bse-private-placement-investor-opinion/`。脚本需要 Python 3 和 `python-docx`：

```bash
python3 -m pip install python-docx
python3 scripts/instantiate_template.py --output /tmp/模拟北交所定增投资方法律意见书_DC_20260818.docx
python3 scripts/audit_opinion.py /tmp/模拟北交所定增投资方法律意见书_DC_20260818.docx --sources assets/legal-source-ledger.template.json
```

正式出具前必须在出具日通过法宝、元典或发布机关官网重新核验法规，并更新事项法律依据台账。`--final` 仅用于审核注册文件已经取得、占位和批注已经清除后的签发前审计。

Skill 说明、方法文档和示例采用 **CC BY-NC 4.0**；独立脚本和 Agent 配置采用 **MIT License**。品牌资产边界见 [`NOTICE.md`](NOTICE.md)。商业授权可联系微信 `Yangyoyo2022` 或邮箱 `yangyoyo2022@qq.com`。
