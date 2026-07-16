# LoCoMo 500 题主实验对比

- Manifest: `data/subsets/locomo10_500q_main_seed42.json`
- 主参照方法: `mragent`
- Conversation-clustered bootstrap: 5000 次

## 总表

| 方法 | 完成 | 额外行 | ERROR | 普通题 F1 | 普通题 Judge | Cat5 | Evidence hit | Tools | Rounds | Runtime(s) | Context |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mragent | 500/500 | 0 | 5 | 0.5252 | NA (0) | 0.8400 | 0.7900 | 7.4180 | 4.7480 | 208.5865 | 2.5460 |
| rag | 500/500 | 0 | 0 | 0.3629 | NA (0) | 0.7600 | 0.7420 | 0.0000 | 0.0000 | 2.1832 | 18.1840 |
| graphrag | 500/500 | 0 | 0 | 0.3517 | NA (0) | 0.7400 | 0.6900 | 0.0000 | 0.0000 | 2.4388 | 22.1840 |

## 分类别结果

| 方法 | 类别 | F1/Accuracy | Judge | Evidence hit |
|---|---:|---:|---:|---:|
| mragent | 1 | 0.4678 | NA | 0.8431 |
| mragent | 2 | 0.6707 | NA | 0.8218 |
| mragent | 3 | 0.3229 | NA | 0.5521 |
| mragent | 4 | 0.6299 | NA | 0.9010 |
| mragent | 5 | 0.8400 | NA | 0.8200 |
| rag | 1 | 0.3869 | NA | 0.8431 |
| rag | 2 | 0.3771 | NA | 0.8218 |
| rag | 3 | 0.1741 | NA | 0.5521 |
| rag | 4 | 0.5039 | NA | 0.8416 |
| rag | 5 | 0.7600 | NA | 0.6400 |
| graphrag | 1 | 0.3311 | NA | 0.8137 |
| graphrag | 2 | 0.4265 | NA | 0.8119 |
| graphrag | 3 | 0.1761 | NA | 0.4479 |
| graphrag | 4 | 0.4647 | NA | 0.7921 |
| graphrag | 5 | 0.7400 | NA | 0.5700 |

## 相对 Full MRAgent 的配对差值

正值表示 Full MRAgent 更好。

| 对比 | 指标 | 配对题数 | 差值 | 95% CI |
|---|---|---:|---:|---:|
| mragent - rag | F1 | 400 | 0.1623 | [0.1361, 0.1900] |
| mragent - rag | Judge | 0 | NA | [NA, NA] |
| mragent - graphrag | F1 | 400 | 0.1735 | [0.1455, 0.2016] |
| mragent - graphrag | Judge | 0 | NA | [NA, NA] |

## 判定规则

- 只有同题、同模型、完整输出的配对结果进入差值；缺题和 ERROR 必须单独报告，不能静默删除。
- 95% CI 不跨 0 才视为当前 10 个 conversation 上的稳定差异；这仍不是论文 50 conversation 的完整复现。
- 普通题统计 cat1-4；cat5 单列，不与论文排除 adversarial 的主表混算。
