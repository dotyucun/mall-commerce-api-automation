# mall-commerce-api-automation

基于真实开源电商系统 `macrozheng/mall` 的前后台接口自动化项目。项目固定被测源码 commit，通过 Docker Compose 启动完整依赖，使用 pytest 驱动前台会员、后台管理、MySQL 与 RabbitMQ 的跨端业务验证。

测试围绕商品可售状态、购物车规则、订单状态机、金额与库存一致性、用户数据隔离、退货闭环和异步超时取消组织；请求、工作流、数据库查询和测试数据治理分别封装。这是基于开源系统的个人测试工程，不是本人开发的电商系统，也不是企业生产环境测试经历。

## 已验证状态

| 项目 | 本地实测结果 |
| --- | --- |
| 被测版本 | `macrozheng/mall@0504e86b1f1b6f1b8aa6a734d37a90fb67346be7` |
| 普通回归 | 默认顺序和逆序结果一致；`21 passed, 9 xfailed, 1 deselected` |
| 完整回归 | `22 passed, 9 xfailed`，包含 RabbitMQ 慢场景 |
| RabbitMQ 慢用例 | `1 passed, 30 deselected`，约 61 秒 |
| 测试收集 | 31 个场景 |
| 框架自测 | Windows `35 passed`；独立验证运行脚本、响应脱敏、数据写入边界、性能业务断言和严格 xfail |
| Locust 基线 | 2026-10-09：20 用户、2 用户/秒、2 分钟；2190 请求、0 失败、聚合 P95 14ms，含业务响应校验 |
| 静态检查 | Ruff check 与 format check 通过 |

9 个预期失败实例对应 6 类已确认源码缺陷，不计入通过数量。原先 8 个实例之外，本轮补充库存断言发现后台关闭未释放锁定库存，并登记 GH-7。`strict=True` 配合专用异常类型，只接受已核实的缺陷表现；连接失败、准备数据失败或其他断言错误仍使回归失败。详见[已知缺陷](docs/known-issues.md)。

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

前置环境：Git、Java 17、Maven、Python 3.12、Docker Desktop。Windows 运行脚本可使用 PowerShell 5.1 或 7，CI 使用 PowerShell 7。Allure 2.24.0 仅在本地生成 HTML 时需要。

```powershell
git clone https://github.com/dotyucun/mall-commerce-api-automation.git
cd mall-commerce-api-automation
Copy-Item .env.example .env
```

在 `.env` 中填写本地专用密码。`bootstrap` 将管理员和两个专用会员的密码初始化为这些值，不要求知道上游演示密码。仓库不保存真实凭据，YAML 只保存非敏感默认值。测试账号密码必须为 1 至 72 个 UTF-8 字节。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 bootstrap
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 test
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 report
```

`bootstrap` 会拉取固定 mall commit、构建两个 JAR、安装测试依赖和本地测试包、启动六个 Compose 服务、等待健康检查，并初始化专用凭据和测试数据。重新执行会恢复测试数据基线，因此不要在测试运行期间执行。端口为后台 8080、前台 8085、MySQL 13307、Redis 6379、MongoDB 27017、RabbitMQ 5672/15672；若占用，先确认占用服务，不要随意结束其他项目进程。

其他命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 full
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 slow
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 verify
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 performance
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 stop
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\mall-test.ps1 down
```

`test` 排除 slow；`full` 包含 RabbitMQ 慢用例；`verify` 只读检查测试数据清理、库存和消息队列。`stop` 停止服务，`down` 删除本项目容器及网络但保留数据卷。测试只能在隔离的 Compose 环境中串行运行，不支持共享环境多进程并发，更不能指向生产数据库或共享生产消息队列。

所有服务端口仅绑定宿主机 `127.0.0.1`，不向局域网开放。固定版本用于复现测试，不是生产环境部署建议。

独立框架自测不需要被测服务：

```powershell
python -m pytest qa -o addopts= -q
```

如果已在当前 PowerShell 会话中导出 `.env` 里的凭据，也可直接按 marker 执行；否则应使用统一脚本，让脚本负责加载 `.env`：

```powershell
python -m pytest -m "smoke"
python -m pytest -m "e2e and not slow"
python -m pytest -m "known_issue"
```

## 报告证据

![Allure Overview](docs/images/allure-overview-20261009.jpg)

![Allure Behaviors](docs/images/allure-behaviors-20261009.jpg)

完整执行环境、限制与原始统计见[实测结果](docs/results.md)。GitHub Actions 会上传 Allure 原始结果、HTML、容器日志和 Locust HTML/CSV，不把生成物提交进源码仓库。

Allure 将 XFAIL 显示为灰色 `skipped`，本次 9 条均为关联 Issue 的已确认缺陷，不是跳过执行。收尾核验及未覆盖范围见[核验清单](docs/final-audit.md)。

## CI

- PR：Ruff、框架自测、收集检查、非 slow 回归、Allure HTML、容器日志。
- main 与手动触发：同样的检查加完整回归，包含 slow。
- 每周及手动触发：RabbitMQ 订单超时慢用例。
- 仅手动触发：Locust 轻量性能基线。

所有工作流都从固定 mall commit 构建真实服务，不使用 Mock 替代被测业务。
