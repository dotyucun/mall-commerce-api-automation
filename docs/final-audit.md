# 项目核验记录

本页汇总 `mall-commerce-api-automation` 在 2026-11-09 的整合核验项与证据。性能实验和报告截图分别保留执行日期，文档更新时间不代表重新完成实验。

2026-10-16 阶梯性能实验记录见[历史实验](performance-20261016.md)，2026-11-09 的四档探索和证据核算见[复核记录](performance-review-20261109.md)。工具、数据和文档纳入同一工程，实验日期与口径仍分别保留。

## 范围与证据

| 核验项 | 证据位置 |
| --- | --- |
| 固定被测源码，不提交上游源码；本轮使用干净构建 | `src/mall_api_test/config/default.yaml`、`scripts/mall-test.ps1`、`.gitignore`、`docs/results.md` |
| 六层职责与统一代码风格 | `docs/architecture.md`、Ruff check/format、`.gitattributes` |
| 35 个业务实例及场景边界 | `docs/test-matrix.md`、pytest 收集 |
| 8 类缺陷对应 13 个严格预期失败 | `docs/known-issues.md`、GitHub Issues #1-5、#7、#11、#12 |
| 默认两轮与逆序一轮回归一致 | `docs/results.md`、`qa/reverse_order_plugin.py` |
| HTTP 与业务错误均保留失败信号 | `qa/test_http_client.py`、`qa/test_known_defects.py` |
| 本地命令失败不会假绿 | `qa/test_runner.py`，覆盖 PowerShell 5.1/7 |
| 凭据来自环境，账号 BCrypt 初始化 | `.env.example`、`scripts/prepare_test_data.py`、`qa/test_data_manager.py` |
| 数据清理和库存恢复可核验 | `scripts/mall-test.ps1 verify`、`docs/test-data.md` |
| MQ 实际超时取消与设置恢复 | `tests/async_workflows/test_order_timeout.py` |
| 读取性能基线与业务响应门禁 | `performance/locustfile.py`、`qa/test_locust_baseline.py` |
| 阶梯读取、窗口记账、资源采集与证据审计 | `performance/step_load.py`、`performance/resource_monitor.py`、`performance/audit.py`、`docs/performance-review-20261109.md` |
| 常规关闭不删除本地数据卷 | `scripts/mall-test.ps1 stop/down` |
| 构建包包含 YAML 配置 | setuptools package-data、wheel 内容核验 |
| GitHub 构建、回归和产物可追溯 | [Actions](https://github.com/dotyucun/mall-commerce-api-automation/actions) |

## 结果解读

业务回归包含 35 个实例，其中 22 个通过、13 个预期失败。预期失败对应 8 类尚未修复的被测系统缺陷，详细说明见[已知缺陷](known-issues.md)。框架自测验证测试工具自身，可以使用 Mock 隔离依赖；业务回归、MQ 和性能任务连接真实 mall 服务。

本轮保留原有本地 SUT 的未提交修改，最终证据来自另建的干净固定版本。串行回归之后，专用购物车、订单、退货和延迟消息均为 0，SKU 库存恢复为 `stock=500`、`lock_stock=0`，超时设置恢复为 120 分钟。默认与逆序一致不等于并行安全，数据重置可能隔离掉共享状态污染，不能夸大该检查的证明力。

本项目的成果是测试工程、缺陷复现和验证证据。被测商城来自开源项目，支付场景使用内部订单状态接口。当前适用环境、已覆盖功能和待扩展范围集中说明在 [README](../README.md#项目范围)。

Locust 包含 20 用户轻量基线及独立阶梯读取实验。未确认生产容量上限；需求覆盖率、效率提升和线上缺陷率尚无统计分母或对照数据，现有实验不支持这些指标结论。

完整执行统计和截图见[实测结果](results.md)。云端验证使用对应提交的 [Actions 记录](https://github.com/dotyucun/mall-commerce-api-automation/actions)。
