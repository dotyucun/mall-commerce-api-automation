# mall-commerce-api-automation

基于真实开源电商系统 `macrozheng/mall` 的前后台接口自动化项目。项目固定被测源码 commit，通过 Docker Compose 启动完整依赖，使用 pytest 驱动前台会员、后台管理、MySQL 与 RabbitMQ 的跨端业务验证。

这不是接口调用脚本集合。测试围绕商品可售状态、购物车规则、订单状态机、金额与库存一致性、用户数据隔离、退货闭环和异步超时取消组织；测试文件只描述场景，请求、工作流、数据库查询和测试数据治理分别封装。

## 已验证状态

| 项目 | 本地实测结果 |
| --- | --- |
| 被测版本 | `macrozheng/mall@0504e86b1f1b6f1b8aa6a734d37a90fb67346be7` |
| 普通回归 | 运行两次结果一致；最终 `22 passed, 8 xfailed, 1 deselected` |
| RabbitMQ 慢用例 | `1 passed, 30 deselected`，约 61 秒 |
| 测试收集 | 31 个场景 |
| Locust 基线 | 20 用户、2 用户/秒、2 分钟；2167 请求、0 失败、聚合 P95 7ms |
| 静态检查 | Ruff check 与 format check 通过 |

`xfail` 不是被隐藏的失败：8 个失败实例对应 5 类已确认源码缺陷，并使用 `strict=True` 防止后端行为变化后仍被误判为预期失败。详见[已知缺陷](docs/known-issues.md)。

## 覆盖范围

- 登录鉴权：前后台登录、错误凭据、Token 身份、未登录访问。
- 商品与购物车：API/数据库一致性、上下架、重复添加、数量更新、库存边界、双用户隔离。
- 订单与金额：确认订单、主表与明细金额、商品快照、锁定库存、取消释放库存。
- 跨端状态机：前台创建与支付、后台发货、前台确认收货、后台关闭、非法流转保护、操作历史。
- 退货：完成订单申请退货、后台审核通过/拒绝、收货完成、删除拒绝申请。
- 异步行为：RabbitMQ 延迟消息自动关闭超时订单，并验证锁定库存释放。
- 性能基线：商品搜索、商品详情和购物车读取的轻量基线，不作为容量或专业压测结论。

不覆盖 UI、真实支付宝、优惠券与积分完整流程、后台权限 CRUD。范围边界是为了保证每个纳入的场景都有可验证的业务结果。

## 工程结构

```text
src/mall_api_test/
  api/             # mall-portal 与 mall-admin 接口对象
  workflows/       # 购物车、订单、退货业务编排
  repositories/    # 只读业务查询与受控测试数据写入
  common/          # HTTP、数据库、轮询、通用与领域断言
  config/          # YAML 默认值和环境变量覆盖
  models.py        # 跨步骤上下文和库存快照
tests/             # 按 auth/product/cart/order/returns/async 分域
docker/            # Compose、服务配置、测试种子数据
scripts/           # 一键启动、测试、报告、性能与清理
performance/       # Locust 基线任务
docs/              # 架构、策略、矩阵、数据、缺陷与实测证据
```

详细分层规则见[架构说明](docs/architecture.md)，完整场景见[测试矩阵](docs/test-matrix.md)。

## 快速开始

前置环境：Git、Java 17、Maven、Python 3.12、Docker Desktop。Allure 2.24.0 仅在本地生成 HTML 时需要。

```powershell
git clone https://github.com/dotyucun/mall-commerce-api-automation.git
cd mall-commerce-api-automation
Copy-Item .env.example .env
```

在 `.env` 中填写本地专用密码。仓库不保存真实凭据，YAML 只保存非敏感默认值。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 bootstrap
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 test
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 report
```

`bootstrap` 会拉取固定 mall commit、构建 `mall-admin`/`mall-portal` JAR、启动 MySQL 5.7、Redis 7、MongoDB 5、RabbitMQ 3.10.5 和两个 Java 服务，并等待健康检查完成。

其他命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 slow
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 performance
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 down
```

如果已在当前 PowerShell 会话中导出 `.env` 里的凭据，也可直接按 marker 执行；否则应使用统一脚本，让脚本负责加载 `.env`：

```powershell
python -m pytest -m "smoke"
python -m pytest -m "e2e and not slow"
python -m pytest -m "known_issue"
```

## 报告证据

![Allure Overview](docs/images/allure-overview.png)

![Allure Behaviors](docs/images/allure-behaviors.png)

完整执行环境、限制与原始统计见[实测结果](docs/results.md)。GitHub Actions 会上传 Allure 原始结果、HTML、容器日志和 Locust HTML/CSV，不把生成物提交进源码仓库。

## CI

- PR、main 与手动触发：Ruff、收集检查、非 slow 回归、Allure HTML、失败日志。
- 每周及手动触发：RabbitMQ 订单超时慢用例。
- 仅手动触发：Locust 轻量性能基线。

所有工作流都从固定 mall commit 构建真实服务，不使用 Mock 替代被测业务。
