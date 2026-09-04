# GradMatch 基础架构实施计划

**目标：** 建立 Web 优先、移动端可迁移的单仓库，并用最小纵向链路验证 Web、API、认证、异步采集和本地基础设施。

**架构：** Next.js App Router 负责 Web 与 SSR；Django、Django Ninja、django-allauth Headless 组成模块化单体；Celery 处理异步采集；PostgreSQL、Redis 与 S3 兼容存储承载数据。TypeScript 客户端从核心 API 与认证 API 的 OpenAPI 契约生成。

**技术栈：** Next.js、React、TypeScript、Tailwind CSS、TanStack Query、React Hook Form、Zod、Django 5.2 LTS、Django Ninja、django-allauth Headless、Celery、PostgreSQL、Redis、HTTPX、selectolax/lxml、Playwright、pnpm、Turborepo、uv、Docker Compose、Caddy。

## 全局约束

- 第一阶段只实现 Web，不创建 Expo 产品页面。
- 共享包不得依赖 DOM、Next.js 或 React Native 专属 API。
- 不定义学校、导师、专业、推荐算法或搜索产品模型。
- 搜索基础设施只使用 PostgreSQL，不接独立搜索引擎。
- 认证由 Django 统一管理；邮箱必须验证，并同时支持密码和一次性验证码。
- Web 使用安全会话 Cookie；未来移动端使用 allauth `X-Session-Token`；不使用 JWT。
- 手机号、微信和 QQ 只预留身份扩展边界，不接外部供应商。
- 采集测试只读取仓库内固定 HTML 测试夹具，CI 不访问真实外部站点。
- 本地使用 Mailpit；生产邮件、域名、服务器地区和 ICP 备案不在本计划内。
- 本地与首台服务器使用 Docker Compose；不使用 Kubernetes、GraphQL 或微服务拆分。

## 任务 1：单仓库基础

建立 pnpm 工作区、Turborepo、严格 TypeScript、uv Python 工程、共享配置、环境变量模板和统一命令。

## 任务 2：Django 核心与系统 API

建立 Django 模块化单体、PostgreSQL 配置、管理后台、Django Ninja，以及 `/api/v1/health/live`、`/api/v1/health/ready`、`/api/v1/meta`。

## 任务 3：认证与生成的 API 客户端

配置 django-allauth Headless 的邮箱注册、强制验证、密码登录、一次性验证码登录和会话；暴露核心与认证 OpenAPI，生成 `coreClient` 与 `authClient`。

## 任务 4：采集纵向链路

建立 `DataSource`、`IngestionRun`、`RawArtifact`、来源适配器协议和 `ingestion.run_source(source_key)`；使用本地 HTML 测试夹具验证快照、解析、去重和任务状态。

## 任务 5：Next.js Web 纵向链路

建立服务端状态页与邮箱注册、验证、密码登录、验证码登录、注销界面；只能使用生成的 API 客户端。

## 任务 6：本地容器栈

建立 Caddy、Web、API、Celery worker/beat、PostgreSQL、Redis、MinIO 和 Mailpit 的 Docker Compose 配置与健康检查。

## 任务 7：CI 与文档

建立格式、代码规范检查、类型检查、单元测试、OpenAPI 漂移、Web 构建、Docker 构建和端到端测试门禁，并记录开发命令和架构边界。

## 任务 8：最终验证

执行 Python、TypeScript、Web、OpenAPI、端到端与容器验证，完成全分支代码审查并记录环境限制。
