# Eval Baseline

运行日期：2026-10-14

| 指标 | 基线结果 |
| --- | ---: |
| Cases | 20 / 20 |
| Pass rate | 100% |
| Grounded recall | 100% |
| Refusal accuracy | 100% |
| Citation accuracy | 100% |

运行命令：

    python -m app.evals

这套基线使用仓库内的自制管理学资料，不调用外部模型。它检查检索、拒答和引用，不评价生成文本的表达质量。后续更改检索或问答逻辑后，应重新运行并与本基线比较。
