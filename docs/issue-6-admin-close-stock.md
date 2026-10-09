# 后台关闭待付款订单没有释放锁定库存

## 环境

- 被测源码：`macrozheng/mall@0504e86b1f1b6f1b8aa6a734d37a90fb67346be7`。
- 本地隔离 Compose；会员 `autotest_a`，商品 26，SKU 110。
- 测试：`test_admin_close_cancels_unpaid_order_and_records_history`。

## 复现

1. 记录 SKU 库存基线 `stock=500, lock_stock=0`。
2. 会员创建数量为 1 的待付款订单，锁定库存增加为 1。
3. 管理员调用 `POST /order/update/close` 关闭该订单。
4. 查询订单、订单操作历史及 SKU 数据库记录。

## 期望与实际

期望：订单状态为 4，关闭历史存在，真实库存不变，锁定库存恢复为 0。

实际：接口成功，订单状态为 4，关闭历史存在，但 SKU 仍为 `stock=500, lock_stock=1`。测试在恢复库存断言处失败。专用数据 fixture 在断言后恢复基线，不将这一步清理当作被测系统修复。

## 源码证据

`mall-admin/src/main/java/com/macro/mall/service/impl/OmsOrderServiceImpl.java` 的 `close()` 只更新订单状态并插入操作历史，没有解除库存锁定。对照 `mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsPortalOrderServiceImpl.java` 的 `cancelOrder()`，后者调用 `releaseSkuStockLock()`；后台关闭后订单已不是状态 0，该前台路径不能再补偿。

## 风险与处置

已关闭订单持续占用可售库存。实验环境可暂停后台关闭操作；正式修复应在合法状态检查、订单关闭及库存释放之间建立事务与幂等约束。不应通过删除断言、直接修改库存或等待测试清理掩盖业务问题。
