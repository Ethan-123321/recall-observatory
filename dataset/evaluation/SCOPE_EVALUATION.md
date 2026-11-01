# 复杂范围核验评估报告

日期：2026-11-01；规则：scope-v5；案例集：scope-eval-20261101。
案例：120；公告来源关联输入36例，来自8份公告；规则规格案例84例。案例作者与版本记录于案例文件。

本轮预期修订8例：批号缺失不再默认免除；旧案例完整保留在scope-cases-v4-preserved.json。

本报告验证明确的规则与边界，不以此推算全部公告上的产品命中准确率。未使用真人实验数据。

- 三分类准确率：100.0%
- 确定性判断覆盖率：60.0%
- 确定性判断准确率：100.0%
- 错误匹配：0；错误排除：0；将待确认错误确定化：0

## 混淆矩阵

| 预期 / 实际 | 符合 | 不符合 | 待确认 |
| --- | ---: | ---: | ---: |
| 符合 | 36 | 0 | 0 |
| 不符合 | 0 | 36 | 0 |
| 待确认 | 0 | 0 | 48 |

## 待确认原因（可重叠）

- missing_batch：8
- date_precision：4
- unsupported_batch：16
- conflict：4
- unresolved_scope：4
- exclusion_unknown：4
- vin：4
- unsupported_model：4
- missing_production：4

## 使用范围

覆盖多组关系、同型号不同日期、跨组拼接、离散日期、月份精度、批号缺失、简称、范围未完整枚举、原文冲突、排除条件、汽车VIN及食品规格缺失。详细输入、预期依据与实际结果见scope-cases.json及scope-results.json。

案例文件SHA256：89f057b1d6be828dd1f5f9eecae1f340a9e1893cf74f4a25a12d4efb20b6ec5b。
正式数据源SHA256：7a2a7038638bf82798fd17ac09dd5d1b1c15b927ee9d85dbdfa23ac15068031c。
