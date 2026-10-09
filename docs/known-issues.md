# 已知缺陷

以下问题均在固定 SUT commit 上通过接口行为、数据库结果和源码路径确认。

| 编号 | 缺陷 | 风险 | 自动化证据 |
| --- | --- | --- | --- |
| [GH-1](https://github.com/dotyucun/mall-commerce-api-automation/issues/1) | 后台发货更新订单失败时仍写入“完成发货”操作记录 | 审计历史与真实订单状态矛盾 | `test_failed_delivery_does_not_write_delivery_history` |
| [GH-2](https://github.com/dotyucun/mall-commerce-api-automation/issues/2) | 支付成功接口缺少幂等保护，重复调用会再次扣减库存 | 库存资产错误 | `test_duplicate_payment_is_rejected_without_second_stock_deduction` |
| [GH-3](https://github.com/dotyucun/mall-commerce-api-automation/issues/3) | 订单详情、取消和支付接口缺少会员所有权校验 | 越权查询和操作他人订单 | `test_user_cannot_access_or_mutate_another_users_order` |
| [GH-4](https://github.com/dotyucun/mall-commerce-api-automation/issues/4) | 退货申请缺少订单所有权和订单完成状态校验 | 越权或非法状态退货 | 两个退货 negative 场景 |
| [GH-5](https://github.com/dotyucun/mall-commerce-api-automation/issues/5) | 商品下架后，旧购物车记录仍可生成订单 | 不可售商品继续成交 | `test_unpublished_product_cannot_be_ordered_from_stale_cart` |
| [GH-7](https://github.com/dotyucun/mall-commerce-api-automation/issues/7) | 后台关闭待付款订单没有释放锁定库存 | 已关闭订单继续占用可售库存 | `test_admin_close_cancels_unpaid_order_and_records_history` |

共 6 类缺陷、9 个测试实例。GH-7 在补充库存一致性断言时暴露，复现细节见[后台关闭库存缺陷](issue-6-admin-close-stock.md)。Issue 编号不是缺陷数量，仓库中的 PR 也占用同一编号序列。

## 管理方式

- 对应测试统一标记 `known_issue` 和 `xfail(strict=True, raises=KnownDefectError)`。
- 普通断言验证准备条件及数据库事实。只有已核实的缺陷表现出现时才抛出专用异常；其他断言、连接或 fixture 错误不得成为 XFAIL。
- Issue 记录复现步骤、期望、实际、风险和相关测试。
- 后端修复后测试会 XPASS 并令 CI 失败，必须删除标记并将其纳入普通回归。

## 能否规避

本项目将被测服务限制在本机隔离环境，以专用账号和数据复现问题。暂停有缺陷的操作可降低演示风险，但隐藏按钮、刷新页面或测试后恢复数据均不代表后端安全或正确。

真正修复需要被测系统修改：订单和退货接口检查当前用户与合法状态；支付使用受信来源及事务内幂等保护；下单重新校验可售状态；发货历史只记录成功操作；后台关闭事务性释放库存。修复后运行现有负向用例及相邻正常流程验证，而不是删除测试。本仓库固定上游版本，不把这些修复建议当作已完成代码。
