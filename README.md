# GradMatch

GradMatch 是一个 Web 优先的单仓库项目，包含 Django API、前后端分离认证和 Next.js 产品基础页面。共享 TypeScript 包保持平台无关，未来的 Expo 应用可以复用业务规则、设计令牌和自动生成的 API 客户端。

## 项目目录

- `apps/web`：基于 Next.js App Router 的最小基础页面。
- `packages/api-client`：根据 Django Ninja 核心 API 和 allauth Headless API 自动生成的 TypeScript 客户端。
- `packages/domain`：共享的 TypeScript 业务契约。
- `packages/design-tokens`：具备类型定义、无浏览器依赖的语义化设计令牌。
- `services/api`：由 uv 管理的 Django 模块化单体，集成 Django Ninja、Admin 和 allauth Headless。

## 产品需求

已确认的产品交互和验收标准记录在[产品需求文档](docs/product-requirements.md)中。新的产品反馈应先补充到该文档，再转化为实施任务。

## 当前进度

已实现内容、验证证据、已知缺口和后续步骤见 [2026-09-04 阶段进度记录](docs/progress/2026-09-04-first-vertical-slice.md)。首个纵向链路仍在开发：后端与共享契约已落地，但新增 Web 决策流程测试引用的组件尚未实现。当前 Web 测试和类型检查不通过，本次检查点不是可发布版本。

本机开发正在转向 Windows 原生服务，Docker Compose 保留为可选部署方式。下方启动说明描述的是早期容器流程，不代表当前原生环境已就绪。原生启动文档和集成验证仍属于任务 10 的待完成内容。

## 常用命令

- `pnpm dev`：启动单仓库的开发进程。
- `pnpm build`：构建全部 TypeScript 工作区包和 Web 应用。
- `pnpm lint`：使用 Biome 检查 JavaScript、TypeScript、JSON 和 Markdown 文件。
- `pnpm typecheck`：对整个工作区执行 TypeScript 严格类型检查。
- `pnpm test`：运行工作区烟雾测试。
- `pnpm format:check`：使用 Biome 检查格式。
- `pnpm generate:api`：导出核心 API 和认证 API 的 OpenAPI 规范，再生成 TypeScript 客户端。
- `pnpm check:api-drift`：重新生成客户端；如果与已提交的契约产物存在差异，则检查失败。
- `pnpm check:compose`：不启动 Docker，仅解析 Compose、检查 Caddy 路由及容器服务、健康检查和密钥边界。
- `pnpm check`：执行 CI 使用的全部 Web/TypeScript 质量检查。
- `pnpm e2e`：使用 Playwright 对 `http://127.0.0.1:8080` 上的 Compose 服务执行端到端测试。

## Windows 环境准备（早期容器流程）

前置依赖：Node.js 22+、pnpm 11+、Python 3.11–3.13；使用完整容器集成环境还需 Docker Desktop。复制本地环境模板并安装前后端依赖：

```powershell
Copy-Item .env.example .env
pnpm install --frozen-lockfile
python -m uv --directory services/api sync --all-groups
```

按照此容器流程在本机开发 API 时，先通过 Compose 启动 PostgreSQL、Redis、MinIO 和 Mailpit，再执行一次数据库迁移：

```powershell
docker compose up -d postgres redis minio minio-init mailpit
python -m uv --directory services/api run python manage.py migrate
python -m uv --directory services/api run python manage.py collectstatic --noinput
```

修改 Django Ninja 或 allauth 接口后，重新生成契约：

```powershell
pnpm generate:api
pnpm check:api-drift
```

使用 `pnpm dev` 启动 Web 工作区进程。早期方案通过 Docker Compose 验证 Web/API 同源访问及端到端认证。编写该启动说明时，本机 Windows 尚未安装 Docker，因此当时无法本地执行 `docker compose config`、镜像构建和端到端测试；CI 在 Linux 上执行这些检查。当前原生运行的验证状态以上方进度记录为准。

## Python 服务

使用限定在 `services/api` 目录下的可移植 `uv` 命令：

```powershell
python -m uv --directory services/api lock
python -m uv --directory services/api run ruff check .
python -m uv --directory services/api run pyright
python -m uv --directory services/api run pytest
```

如果 `uv` 已加入 `PATH`，也可以从仓库根目录执行以下等效命令：

```powershell
uv --directory services/api lock
uv --directory services/api run ruff check .
uv --directory services/api run pyright
uv --directory services/api run pytest
```

## 认证与 API 契约

- `GET /api/v1/health/live`、`GET /api/v1/health/ready` 和 `GET /api/v1/meta` 提供初始系统契约。
- `/_allauth/*` 提供邮箱注册、邮箱验证、密码登录、一次性验证码登录、注销和 Headless OpenAPI 文档。
- 浏览器客户端使用安全的 HttpOnly 会话 Cookie 认证；未来移动端使用 allauth 的 `X-Session-Token`。GradMatch 不签发 JWT。
- 本地邮件投递到 `EMAIL_SMTP_*` 指定的 SMTP 主机；Docker Compose 会将这些变量指向 Mailpit。

## 本地容器服务

Docker Compose 是首个部署目标：Caddy 为浏览器提供统一访问源，Django 处理 API、allauth、admin 及 static/media 路径，Next.js 处理其余页面。PostgreSQL、Redis、MinIO、Mailpit、Celery worker/beat 和一次性迁移服务保留在服务栈内部。

```powershell
Copy-Item .env.example .env
docker compose up --build --wait
```

访问 `http://localhost` 打开 GradMatch，访问 `http://localhost:8025` 打开 Mailpit。一次性 `migrate` 服务会在 API、worker 或 beat 进程启动前执行迁移，并将静态文件收集到 API 以只读方式挂载的共享卷。使用 `docker compose down` 停止服务；只有明确需要丢弃本地 PostgreSQL、MinIO 和静态文件数据时，才添加 `--volumes`。

已提交的 `.env.example` 中仅包含开发用占位值。复制得到的 `.env` 应只保留在本机；任何接近部署用途的环境都应使用足够长且独立的 Django 密钥，切勿提交真实凭据。

## 采集基础能力

- `gradmatch.ingestion` 是由 Celery 驱动的模块化单体应用。`ingestion.run_source` 记录每次运行，并通过 Celery 对运行故障执行重试。
- 首个 `smoke-fixture` 来源只读取 `services/api/tests/fixtures/sample-source.html`，不会请求真实公开网站。
- 原始来源字节按 SHA-256 去重，并通过兼容 S3 的产物存储接口保存。后续适配器可以使用 HTTPX 或 Playwright 抓取接口，无需改变任务运行生命周期。

## 范围说明

当前仓库阶段暂不包含移动端应用，Expo 支持留待后续任务。
