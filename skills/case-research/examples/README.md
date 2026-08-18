# case-research 模拟示例

`模拟案例.json` 为从零构造的完整归档样例，不对应真实案件。

```bash
python3 ../scripts/case_json_lint.py 模拟案例.json
python3 ../scripts/case_table_from_json.py 模拟案例.json
python3 ../scripts/search_case_json.py 模拟 --root .
```

参考工作簿见 `../reference-workbooks/`，仅用于观察复杂专题表结构。
