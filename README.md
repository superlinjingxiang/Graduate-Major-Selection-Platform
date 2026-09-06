# GradMatch

GradMatch 是一个面向研究生报考决策的 Web 优先单仓库。当前首个纵向链路聚焦 2027 年北京、全日制、全国统考、计算机相关方向；系统用可追溯证据给出资格三态、候选比较和决策快照，不提供录取概率或“冲稳保”承诺。

## 项目目录

- `apps/web`：Next.js App Router Web 应用，公开目录由服务端渲染，交互流程使用生成客户端。
- `services/api`：Django 模块化单体，包含 Django Ninja、allauth Headless、Admin、Celery 和领域数据。
- `packages/api-client`：由核心 API 和 allauth OpenAPI 自动生成的 TypeScript 客户端。
- `packages/domain`：不依赖浏览器、Next.js 或 React Native 的共享业务契约。
- `packages/design-tokens`：跨平台语义化颜色、排版、间距、圆角、阴影和动效令牌。
- `docs`：中文产品需求、架构、研究范围和进度记录。

## 当前进度

首个纵向链路的代码已经覆盖以下流程：冻结试点目录、确认用户事实、三个工程项目的资格三态、确定性比较、访客决策快照、账户认领、纠错审核发布，以及同一事务出箱事件重复处理时的幂等重算。工程验收同时验证旧结果和旧快照保持不变，`synthetic`、`test_fixture` 与 `reference_year=2026` 测试数据不会进入公开响应。

Web 端已提供试点项目目录、事实确认、比较结果、决策快照和纠错入口。AI、真实支付、移动端页面和真实外部来源采集保持关闭。2027 年正式规则尚未发布时，真实项目只能返回“需要确认”，不能被测试夹具提升为确定结论。

本地开发采用 Windows 原生进程，Docker Compose 仅作为可选的单机部署与 CI 验证方式。运行状态以 `pnpm status:native` 的实时输出为准；代码检查通过不代表本机 PostgreSQL、Redis 或对象存储已经启动。

## Windows 原生开发

### 1. 前置依赖

- Node.js 22 或更高版本、pnpm 11 或更高版本；
- Python 3.11–3.13，项目推荐使用 `uv`；
- 独立安装并启动 PostgreSQL、Redis 兼容服务和 S3 兼容对象存储；
- 需要测试注册邮件时，再启动本地 SMTP 捕获服务（例如 Mailpit）。

复制环境模板并安装依赖：

```powershell
Copy-Item .env.example .env
pnpm install --frozen-lockfile
python -m uv --directory services/api sync --all-groups
```

`.env.example` 默认指向 `localhost:5432`、`localhost:6379`、`localhost:9000`、API 的 `localhost:8000` 和 Web 的 `localhost:3000`。复制后请把占位密码改为本机服务的实际凭据；`.env` 不得提交。

### 2. 检查本机依赖

```powershell
pnpm status:native
```

该命令只执行读取和连接检查：导入 Python 项目包、对 PostgreSQL 执行 `SELECT 1`、对 Redis 执行 `PING`、检查 S3 bucket，并报告 8000/3000 端口是否占用。它不会启动、停止或修改服务；任一必需依赖不可用时以非零状态退出。

### 3. 迁移并启动后端

在第一个 PowerShell 窗口执行迁移和 API：

```powershell
Set-Location services/api
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe -m uvicorn gradmatch.config.asgi:application --host 127.0.0.1 --port 8000 --reload
```

在第二、第三个窗口分别启动 Celery worker 和 beat。Windows 开发环境的 worker 使用 `solo` 池：

```powershell
Set-Location services/api
.\.venv\Scripts\python.exe -m celery -A gradmatch worker --loglevel=INFO --pool=solo
```

```powershell
Set-Location services/api
.\.venv\Scripts\python.exe -m celery -A gradmatch beat --loglevel=INFO
```

Celery 任务入口和幂等重算已经实现；定时调度是否实际触发仍取决于 worker、beat、Redis 以及已配置的调度项，不能仅凭进程启动推断业务事件已自动消费。

### 4. 启动 Web

在仓库根目录的新窗口执行：

```powershell
pnpm --filter @gradmatch/web dev
```

浏览器打开 `http://localhost:3000`。Next.js 会把 `/api/*`、`/_allauth/*`、`/accounts/*`、`/admin/*`、`/static/*` 和 `/media/*` 转发给本机 Django，因此浏览器继续使用同源 Cookie 与统一 CSRF 处理。

后端启动后可在终端验证内部就绪接口：

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

就绪接口用于开发和运维，不应放到普通用户页面。

## 常用检查命令

- `pnpm check`：执行格式、lint、类型检查、测试、Python 检查、构建、OpenAPI 漂移、Compose 静态检查和 CI 配置检查。
- `pnpm check:api-drift`：重新生成核心 API 与认证客户端，并检查是否存在未提交的契约漂移。
- `pnpm --filter @gradmatch/web build`：单独构建 Web 应用。
- `pnpm test:tooling`：测试 Python 运行时发现和本机状态诊断脚本。
- `pnpm e2e`：对已启动的完整服务运行浏览器端到端测试。

Python 项目也可单独检查：

```powershell
python -m uv --directory services/api run ruff check .
python -m uv --directory services/api run pyright
python -m uv --directory services/api run pytest
```

修改 Django Ninja 或 allauth 接口后执行：

```powershell
pnpm generate:api
pnpm check:api-drift
```

## 可选 Docker Compose

Docker 不是本机功能开发的前置条件。需要复现单机服务栈时，Compose 会启动 Caddy、Web、API、Celery worker/beat、PostgreSQL、Redis、MinIO 和 Mailpit，并由一次性迁移服务执行数据库迁移：

```powershell
Copy-Item .env.example .env
docker compose up --build --wait
```

Compose 明确覆盖容器内部主机名与对外 Web 地址，因此 `.env.example` 的原生 `localhost` 地址不会被带入容器间连接。访问 `http://localhost` 打开 GradMatch，访问 `http://localhost:8025` 打开 Mailpit。停止服务使用 `docker compose down`；只有明确要删除本地持久化数据时才添加 `--volumes`。

## 产品与安全边界

- 浏览器使用 Django 的 Secure、HttpOnly、SameSite 会话 Cookie；未来 Expo 使用 allauth `X-Session-Token`，不引入 JWT。
- PostgreSQL 是业务事实的权威来源；Redis 只保存临时任务状态，对象存储保存不可变来源数据块和派生产物。
- 首个真实来源接入前仍需完成来源权利、安全、审核和发布门禁；测试只使用本地 fixture，不访问真实网站。
- AI、支付和移动端当前均未启用，不能通过功能开关绕过相应治理门禁。

详细行为见[产品需求文档](docs/product-requirements.md)，技术约束见[架构基线](docs/architecture.md)，冻结项目分母见[试点范围](docs/research/pilot-scope-2027-v1.md)。
