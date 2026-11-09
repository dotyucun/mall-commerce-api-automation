# 购物车越权与非正数量缺陷

被测版本固定为 `macrozheng/mall@0504e86b1f1b6f1b8aa6a734d37a90fb67346be7`。以下场景于 2026-11-09 在本地隔离环境重新执行，4 个实例均触发对应的 `KnownDefectError`，结果为严格 XFAIL；未修改商城源码。

## GH-11：修改规格可以删除其他会员的购物车记录

- 缺陷记录：[GH-11](https://github.com/dotyucun/mall-commerce-api-automation/issues/11)。
- 用例：`test_user_cannot_replace_another_users_cart_item_attributes`。
- 会员 A 与 B 分别登录，使用独立 HTTP Session；A 添加专用商品，记录返回的购物车 ID。
- B 调用 `POST /cart/update/attr`，请求体包含 A 的购物车 ID，其余字段来自合法商品规格。
- 期望：拒绝该操作，A 的记录保持不变，B 的购物车不新增商品。
- 本轮实际观察：业务码为 200，A 的购物车列表为空，B 的购物车出现相同 SKU 的一条记录。

该用例通过两个用户各自的列表接口验证影响，没有直接对购物车表做数据库断言，不能将接口观测写成已保存的数据库快照。

源码位置：`mall-portal/src/main/java/com/macro/mall/portal/service/impl/OmsCartItemServiceImpl.java` 的 `updateAttr()`。它按主键更新原记录的删除标记，然后调用 `add()` 为当前会员添加记录。原记录更新没有会员条件；相邻的 `delete()`、`updateQuantity()` 则包含会员条件。

## GH-12：非正数量可进入购物车并产生负金额订单

- 缺陷记录：[GH-12](https://github.com/dotyucun/mall-commerce-api-automation/issues/12)。
- 加购用例：`test_cart_rejects_non_positive_quantity`，分别传入数量 0、-1。
- 期望：拒绝非正数量，购物车保持为空。
- 本轮实际观察：加购业务码为 200，列表保存了相应的 0 或 -1 数量。

负数量下单用例：`test_negative_cart_quantity_cannot_produce_order`。

1. 查询 SKU 库存快照，正常添加一件商品。
2. 调用 `GET /cart/update/quantity` 将该购物车记录数量改为 -2。
3. 使用该记录生成确认订单，再提交订单。
4. 查询订单主表、明细和 SKU 库存。

期望是修改数量或下单阶段拒绝非法输入，不能生成负金额订单。本轮用例确认生成订单的业务码为 200，数据库 `pay_amount < 0`、明细 `product_quantity = -2`，真实库存不变，锁定库存较操作前减少 2。当前断言检查金额为负，没有断言固定金额，因此这里不将历史 Issue 中的绝对金额作为本轮查库快照。

源码位置：同一购物车实现类的 `add()`、`updateQuantity()` 没有数量为正的校验。订单服务仍使用购买数量计算金额与锁定库存。这是测试环境中的资产一致性缺陷复现，未涉及真实支付或生产损失。

## 结果判定与清理边界

只有核对到上述缺陷特征，才抛出 `KnownDefectError` 并计为 XFAIL。请求错误、普通断言错误和环境故障仍会导致失败。`strict=True` 会让不再复现缺陷的正常返回产生 XPASS 失败信号，提醒复核缺陷状态和用例预期。

四个实例通过 `clean_test_data` 在前后重置专用用户数据、恢复固定商品和 SKU 库存，并清理专用延迟队列。数据重置不会修复后端缺陷；这些用例只能串行运行，不能与 Postman 写操作或其他测试进程共享该环境。
