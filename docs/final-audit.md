# 收尾核验清单

核验日期：2026-10-09。主项目是本仓库 `mall-commerce-api-automation`，不是早期 `mall-tiny-api-test`。

## 范围与证据

| 核验项 | 证据位置 |
| --- | --- |
| 固定被测源码，无源码复制或后端修改 | `config/default.yaml`、`scripts/mall-test.ps1`、`.gitignore` |
| 六层职责与统一代码风格 | `docs/architecture.md`、Ruff check/format、`.gitattributes` |
| 31 个业务实例及场景边界 | `docs/test-matrix.md`、pytest 收集 |
| 6 类缺陷对应 9 个严格预期失败 | `docs/known-issues.md`、GitHub Issues #1-5、#7 |
| 默认与逆序回归一致 | `docs/results.md`、`qa/reverse_order_plugin.py` |
| HTTP 与业务错误均保留失败信号 | `qa/test_http_client.py`、`qa/test_known_defects.py` |
| 本地命令失败不会假绿 | `qa/test_runner.py`，覆盖 PowerShell 5.1/7 |
| 凭据来自环境，账号 BCrypt 初始化 | `.env.example`、`scripts/prepare_test_data.py`、`qa/test_data_manager.py` |
| 数据清理和库存恢复可核验 | `scripts/mall-test.ps1 verify`、`docs/test-data.md` |
| MQ 实际超时取消与设置恢复 | `tests/async_workflows/test_order_timeout.py` |
| 读取性能基线与业务响应门禁 | `performance/locustfile.py`、`qa/test_locust_baseline.py` |
| 常规关闭不删除本地数据卷 | `scripts/mall-test.ps1 stop/down` |
| 构建包包含 YAML 配置 | setuptools package-data、wheel 内容核验 |
| GitHub 构建、回归和产物可追溯 | [Actions](https://github.com/dotyucun/mall-commerce-api-automation/actions) |

## 交付边界

- 这是基于开源系统的个人测试工程，不是本人开发商城、企业实习或生产上线经历。
- 测试工程可完成并交付，同时被测版本仍存在开放缺陷；XFAIL 不等于通过或修复，不能表述为被测商城已可安全投产。
- 被测环境只绑定本机端口，测试专用账号与数据串行使用。不支持指向生产、共享业务队列或并发修改同一 SKU。
- 支付调用是被测系统内部订单状态接口，不是支付宝沙箱交易或真实支付；没有 UI 自动化、完整优惠券/积分、生产部署流水线。
- Locust 只是 20 用户读取基线，没有验证高并发下单、库存竞争、生产容量或长时间稳定性。
- 框架自测可使用 Mock 隔离依赖；电商业务回归、MQ 和性能任务使用真实 mall 服务，不以 Mock 替代验收。
- 不声称需求覆盖率、效率提升或线上缺陷率，没有相应统计分母和对照数据。

完整执行统计和报告截图见[实测结果](results.md)。云端是否成功以对应提交的 Actions 结果为准，不将历史绿色运行当作新代码验证。
