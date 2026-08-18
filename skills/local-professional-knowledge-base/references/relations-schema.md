# 跨材料比较与关系 Schema

知识迭代分两步：机器召回候选，模型阅读确认。二者不可混同。

## `待比较.jsonl`

脚本对本次新增或内容变化的材料生成一行，包含：

- `material_id`：待比较材料；
- `change_type`：`added` 或 `modified`；
- `candidate_material_ids`：按词项、标题和明确引用召回的候选旧材料；
- `candidate_scores`：仅供排序的召回分数；
- `reason`：为什么进入队列。

分数不证明法律或知识关系。候选为空也不证明没有关联材料。

## 比较维度

法规：发布机关、效力层级、发布日期、施行日、失效/废止状态、修订条款、过渡规则、适用范围。

案例：法院与审级、案号、争点、事实前提、裁判理由、法律依据、裁判结果、是否具有指导或典型效力。

文章与书籍：作者和时间、引用依据、论证前提、结论边界、后续规则或案例是否改变其基础。

## `relations.jsonl`

只有阅读双方材料并能说明证据时才写入。每行结构：

```json
{"relation_id":"rel-...","from_material_id":"mat-...","to_material_id":"mat-...","relation_type":"revises","basis":"明确写明修订对象及条款","evidence":[{"material_id":"mat-...","location":"第X条/标题","quote":"必要的短引文"}],"confidence":"confirmed|needs_review","note":"适用边界或细微差异","recorded_at":"ISO 8601 时间"}
```

允许的 `relation_type`：

| 类型 | 含义 |
|---|---|
| `revises` | 明确修订另一材料 |
| `repeals` | 明确废止或取代另一材料 |
| `cites` | 明确引用另一材料 |
| `interprets` | 对另一规则作解释 |
| `applies` | 在具体事实中适用另一规则 |
| `conflicts` | 在可比前提下存在实质不一致 |
| `distinguishes` | 因事实或适用条件不同而区分 |
| `supplements` | 增加另一材料未覆盖的规则或判断 |

同题、相似关键词、时间较新、结论不同，都不足以单独证明 `revises`、`repeals` 或 `conflicts`。

`confidence=needs_review` 只用于已有明确迹象但尚需人工确认；不得把纯猜测写入 relations。关系变化时不要静默覆盖旧行：新增一条关系记录，并在 `note` 说明前一判断为何调整。
