# 律师函事项 JSON

## 目录

- 顶层事项
- 策略和签发状态
- 事实与证据
- 固定 11 部分正文
- 草稿和签发稿

## 顶层事项

~~~json
{
  "status": "draft",
  "lawyer_confirmed": false,
  "purpose": "要求对方限期履行并保留后续救济",
  "client": "委托人全称",
  "recipient": "收件人全称",
  "recipient_address": "",
  "matter": "合同履行争议",
  "requested_outcome": "限期履行、书面反馈",
  "nonperformance_consequence": "依法评估诉讼、保全或其他救济",
  "strategy_analysis": {},
  "issuance": {},
  "facts": [],
  "legal_sources": [],
  "document": {}
}
~~~

purpose 是为什么发函；matter 是法律关系和事由；requested_outcome 是要求对方做什么；nonperformance_consequence 是到期未履行时委托人拟采取的下一步行动。不要互相代替。

## 策略和签发状态

~~~json
{
  "strategy_analysis": {
    "advantages": ["现有材料可以证明合同及催告"],
    "disadvantages": ["部分履行和损失范围尚未核实"],
    "risks": ["过早作出严重定性可能压缩谈判空间"],
    "goal_fit": "律师函可用于正式催告和固定立场，但不能替代证据保全"
  },
  "issuance": {
    "engagement_completed": false,
    "strategy_confirmed_by_client": false,
    "letter_confirmed_by_client": false
  }
}
~~~

策略分析供模型和律师使用，不直接照搬进正文。draft 可先形成审阅稿；final 除 lawyer_confirmed: true 外，三个 issuance 字段必须为 true。

## 事实与证据

~~~json
{
  "statement": "收件人在公众号中使用委托人注册商标",
  "include_in_letter": true,
  "evidence": ["公众号页面截图及链接"],
  "basic_evidence_needed": [
    "带时间戳的完整页面取证",
    "商标注册证或其他权利证明"
  ],
  "lawyer_decision": "qualify"
}
~~~

lawyer_decision：

- confirmed_with_evidence：律师确认事实且已有相应证据；
- confirmed_without_evidence：律师知悉证据缺口后仍决定写入；
- qualify：使用“据委托人陈述”“根据现有材料”等限定；
- omit：不写入律师函；
- null：尚待律师选择，草稿允许，签发稿不允许。

证据为空不阻止草稿。没有证据时仍须列最基础应有证据并提示律师核实。

法律来源：

~~~json
{
  "name": "中华人民共和国民法典",
  "article": "第五百七十七条",
  "proposition": "违约方承担继续履行、补救或赔偿损失等责任",
  "verified": true,
  "source": "元典 MCP 返回的法条链接或项目内已核验来源"
}
~~~

正文不列具体条号时可不创建 legal_sources。一旦写入条号或明确规则，必须核验。

## 固定 11 部分正文

~~~json
{
  "document": {
    "title": "律 师 函",
    "reference_prefix": "川大成函字",
    "reference_no": "",
    "subject": "关于要求立即履行合同义务之事宜",
    "recipient_line": "致：某某有限公司",
    "opening": [
      "北京大成（成都）律师事务所依法接受某某有限公司的委托，指派本律师就……事宜，向贵司出具本律师函。"
    ],
    "main_basis": {
      "fact_basis": [
        "双方签署的合同及附件",
        "付款凭证及催告记录"
      ],
      "legal_basis": [
        "《中华人民共和国民法典》第五百零九条、第五百七十七条"
      ]
    },
    "basic_facts": [
      "根据委托人提供的材料，……"
    ],
    "legal_liability": [
      "依据合同约定及相关法律规定，……"
    ],
    "lawyer_opinion": [
      {
        "text": "请贵司于收到本函之日起五日内……",
        "bold": true
      },
      "如未按期履行，委托人将……"
    ],
    "closing": [
      "为避免争议进一步扩大并造成不必要损失，望贵方审慎对待本函所述事实、法律责任及本律师意见，及时作出实质、有效回应。"
    ],
    "copy_statement": "本函一式两份，一份送达贵方，一份留存本所备查。",
    "closing_phrase": "特此函告。",
    "firm": "北京大成（成都）律师事务所",
    "lawyers": [],
    "issue_date": "",
    "stamp_note": "（本函加盖本所公章及骑缝章后发出）",
    "attachments": [],
    "no_attachments": false
  }
}
~~~

对应关系：

1. 标题：title；
2. 案号：reference_no；草稿为空时自动生成“编号：（当年）川大成函字第〔待编号〕号”；
3. 摘要：subject 与 recipient_line；
4. 首部：opening；
5. 主要依据：main_basis.fact_basis 与 main_basis.legal_basis；
6. 基本事实：basic_facts；
7. 法律责任：legal_liability；
8. 本律师意见：lawyer_opinion，必须包含请求、期限、反馈和不履行后果；
9. 结尾：closing、copy_statement、closing_phrase；
10. 签署：firm、两名 lawyers、issue_date、stamp_note；
11. 附件：attachments；确认无附件时设置 no_attachments: true。

正文段落可写成字符串，也可写成 {"text": "...", "bold": true} 以突出核心请求。不得用可变的 sections 取代固定 11 部分；生成器仅为旧数据保留兼容读取。

## 草稿和签发稿

draft：

- 允许证据、编号、律师姓名和附件状态尚未补齐；
- 编号为空时自动保留待编号；律师姓名不足两名时自动保留两处手签栏；
- 日期为空时按生成当日中国标准时间预填中文日期，须律师据实修改；
- 附件未确定时保留醒目提示；
- 所有缺口由验证器输出警告，不另行生成审查单。

final：

- lawyer_confirmed: true；
- 委托、策略和函稿已按 issuance 确认；
- 固定 11 部分全部有实际内容；
- reference_no、两名律师、日期、附件或“无附件”均已据实填写；
- 不含“待确认、待补充、待编号、XX、TBD、TODO”等占位符；
- 每项写入函件的重要事实已有律师选择；
- 法律依据已经核验，或正文有意不列具体条号。

证据没有全部取得不当然阻止签发；但律师必须知悉缺口并选择确认、限定表述或删除。
