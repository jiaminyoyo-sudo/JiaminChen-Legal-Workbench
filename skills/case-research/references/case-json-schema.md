# 案例全文 JSON 归档模板

保存为 UTF-8 JSON。字段可增补，但不得删除完整性检查字段。

```json
{
  "archive_version": "1.0",
  "retrieved_at": "2026-06-17T20:00:00+08:00",
  "retrieved_by": "lawyer",
  "matter": {
    "matter_name": "事项名",
    "matter_path": "./",
    "local_archive_path": "./case-json/YYYY-MM-DD_事项名/案号_法院_简短案名.json"
  },
  "source": {
    "database": "北大法宝 / 华语原典 / 中国裁判文书网 / 法院官网 / 其他",
    "source_url": "https://example.com",
    "source_id": "数据库内部 ID，如有",
    "access_method": "MCP详情接口 / 浏览器详情页 / 导出 / PDF OCR / 其他",
    "query_used": "检索式或关键词",
    "verification_url": "可复核链接"
  },
  "case_metadata": {
    "case_name": "案例名称",
    "case_number": "案号",
    "court": "审理法院",
    "court_level": "最高院/高院/中院/基层/专门法院/待确认",
    "case_type": "民事/刑事/行政/执行/其他",
    "doc_type": "判决书/裁定书/决定书/调解书/其他",
    "decision_date": "YYYY-MM-DD",
    "cause_of_action": "案由",
    "parties": ["当事人1", "当事人2"],
    "keywords": ["关键词1", "关键词2"]
  },
  "full_text_status": "complete",
  "not_complete_reason": "",
  "next_retrieval_steps": "",
  "sections": {
    "title": "文书标题",
    "parties": "当事人信息原文",
    "claims": "诉讼请求/上诉请求原文",
    "facts": "事实认定原文",
    "court_reasoning": "本院认为原文",
    "judgment_result": "裁判结果原文",
    "full_text": "裁判文书全文"
  },
  "excerpts": [
    {
      "purpose": "拟证明的裁判观点",
      "quote": "本院认为原文摘录",
      "section": "court_reasoning"
    }
  ],
  "source_materials": [
    {
      "material_type": "法答网 / 法院公众号 / 微信公众号 / 律所文章 / 法院官网文章 / 其他",
      "title": "文章或问答标题",
      "publisher": "发布主体",
      "published_at": "YYYY-MM-DD 或待确认",
      "url": "https://example.com",
      "retrieved_at": "2026-06-17T20:00:00+08:00",
      "source_priority": "A1/A2/A3/B1/B2/C/待评估",
      "used_for": "发现案例 / 观点线索 / 规则线索 / 排除",
      "viewpoint_summary": "文章、问答或实务材料的核心观点摘要，需具体到可供用户判断的观点",
      "cited_rules_summary": "文章引用或依据的法规、司法解释、会议纪要、裁判规则、监管规则摘要；没有则写未直接引用",
      "cited_cases": ["文章明确提到的案号、案例名或裁判来源"],
      "notes": "与本案例或问题的关系；如未采用，写明排除原因"
    }
  ],
  "reuse_notes": {
    "issues": ["可复用问题标签"],
    "supports": "本案原文可支撑的命题，简要内部备注",
    "does_not_support": "本案不能支撑的命题，简要内部备注",
    "boundaries": "适用边界，简要内部备注"
  },
  "integrity": {
    "full_text_char_count": 0,
    "sha256": "full_text 的 SHA-256",
    "has_court_reasoning": true,
    "has_judgment_result": true,
    "checked_complete": true
  }
}
```

## 完整性规则

- `full_text_status` 只能使用：`complete`、`partial`、`snippet_only`、`metadata_only`。
- 只有 `sections.full_text` 包含完整裁判文书正文时，才能写 `complete`。
- 若语义检索只返回摘要、裁判要旨、部分“本院认为”，应写 `snippet_only` 或 `partial`。
- `source_materials` 用于源素材留痕，尤其记录法答网、法院公号、微信公众号和实务文章链接；它不替代案例原文。
- 每条采用或重要排除的源素材，原则上应填写 `viewpoint_summary`、`cited_rules_summary` 和 URL。不得只写“规则背景”“文章线索”等无法复核的空泛描述。
- `reuse_notes` 是内部复用备注，不等于交付表格字段；对外表格不展示“适用说明”类字段，除非用户另行要求。
