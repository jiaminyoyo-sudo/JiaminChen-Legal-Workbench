# 法宝链接补全文与 txt 入库流程

适用场景：北大法宝 MCP、语义检索或搜索结果只返回案例元数据、摘要、裁判要旨、部分本院认为、identified 字段或片段，但用户交付需要引用该案例。

## 强制口径

1. 片段只能作为线索，不能标记为完整全文。
2. 正式引用前，应沿案例链接进入详情页，取得裁判文书全文。
3. 法宝页面可用下载按钮时，优先选择 txt 下载；其次复制网页全文；再其次使用 PDF/OCR 或其他可复核来源。
4. 只有 txt、网页全文或等价全文已写入 sections.full_text，且包含当事人、诉讼请求或上诉请求、事实认定、本院认为、裁判结果，才能标记 full_text_status 为 complete。
5. 若页面无法访问、无下载权限或全文不可得，保存为 partial 或 snippet_only，并写明 not_complete_reason 和 next_retrieval_steps。

## 操作步骤

1. 从 MCP 结果记录案号、标题、法院、裁判日期、gid、法宝链接、检索式。
2. 用浏览器或 web-access 打开法宝链接。
3. 在详情页查找下载按钮，优先选择 txt。
4. 将下载得到的 txt 保存到当前事项 work 或 case-json 附近的临时位置。
5. 使用 scripts/pkulaw_txt_to_case_json.py 将 txt 合并进既有线索 JSON，或生成新的完整 JSON 草稿。
6. 使用 scripts/case_json_lint.py 校验完整性。
7. 从完整 JSON 中摘录本院认为原文；不要再使用语义检索片段替代法院说理。

## txt 入库后的检查

- sections.full_text 字数通常应显著大于语义检索片段。
- sections.court_reasoning 应尽量保留完整本院认为；如脚本切分不准，手工修正。
- excerpts.quote 应从 sections.court_reasoning 中摘录，尽量保持原文。
- integrity.full_text_char_count 和 integrity.sha256 应与 sections.full_text 一致。

## 源素材文章与案例全文的关系

法答网、法院文章、公众号文章、律所文章可以帮助发现案例或理解规则，但不能替代裁判文书全文。源素材记录必须保留 URL、发布主体、核心观点摘要、引用法规/规则摘要；案例表引用仍以倒查后的裁判文书原文为准。
