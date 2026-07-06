# 已知缺陷

以下问题均在固定 SUT commit 上通过接口行为、数据库结果和源码路径确认。正式发布后，GH 编号将链接到仓库 Issue。

| 编号 | 缺陷 | 风险 | 自动化证据 |
| --- | --- | --- | --- |
| GH-1 | 后台发货更新订单失败时仍写入“完成发货”操作记录 | 审计历史与真实订单状态矛盾 | `test_failed_delivery_does_not_write_delivery_history` |
| GH-2 | 支付成功接口缺少幂等保护，重复调用会再次扣减库存 | 库存资产错误 | `test_duplicate_payment_is_rejected_without_second_stock_deduction` |
| GH-3 | 订单详情、取消和支付接口缺少会员所有权校验 | 越权查询和操作他人订单 | `test_user_cannot_access_or_mutate_another_users_order` |
| GH-4 | 退货申请缺少订单所有权和订单完成状态校验 | 越权或非法状态退货 | 两个退货 negative 场景 |
| GH-5 | 商品下架后，旧购物车记录仍可生成订单 | 不可售商品继续成交 | `test_unpublished_product_cannot_be_ordered_from_stale_cart` |

## 管理方式

- 对应测试统一标记 `known_issue` 和 `xfail(strict=True)`。
- 预期失败只包围已确认缺陷，不放宽断言，不使用 `skip` 隐藏。
- Issue 记录复现步骤、期望、实际、风险和相关测试。
- 后端修复后测试会 XPASS 并令 CI 失败，必须删除标记并将其纳入普通回归。
