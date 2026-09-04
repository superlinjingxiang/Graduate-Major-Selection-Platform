# GradMatch 首个纵向链路实施计划

> **面向执行代理：** 必须使用 `superpowers:subagent-driven-development` 技能逐项执行本计划；每项任务都分配新的实现代理，并单独进行评审。

**目标：** 围绕已冻结的 2027 年北京全日制计算机相关统考试点，交付 GradMatch 首个可信的端到端决策链路，覆盖来源证据、确定性资格判断、比较、访客决策快照、纠错与幂等重算。

**架构：** 在现有 Django 模块化单体中扩展证据、目录、决策建议和支持模块。PostgreSQL 作为权威数据源，Redis/Celery 负责异步任务，S3 兼容存储保存不可变原始数据块，Django Ninja 提供版本化 API，自动生成的 TypeScript 客户端承载接口契约，Next.js 服务端组件与职责范围明确的客户端组件构建 Web 体验。决策结果进行版本管理，并可通过不可变输入复现；生产数据与合成测试数据在存储层及服务边界均保持隔离。

**技术栈：** Django 5.2 LTS、Django Ninja、django-allauth Headless、PostgreSQL、Redis、Celery、S3 兼容对象存储、Python 3.12、uv、pytest、Ruff、Pyright、Next.js App Router、React、TypeScript 严格模式、pnpm、Turborepo、Zod、TanStack Query、Tailwind CSS。

**需求依据：** `docs/product-requirements.md`、`docs/architecture.md`、`docs/research/pilot-scope-2027-v1.md` 和 `docs/research/validation-protocol-v1.md`。

## 阶段进度检查点 — 2026-09-04

任务 1–8 已有实现提交；任务 9 仅有测试草稿，由于页面和组件尚未实现，当前测试失败。任务 10 和发布验证仍未完成。最新检查结果、已知缺口及后续优先事项见[进度记录](../../progress/2026-09-04-first-vertical-slice.md)。本计划尚未完成。下方 Web 路径应按实际的 `apps/web/src/app`、`apps/web/src/features` 和 `apps/web/src/lib` 目录结构解析。

## 全局约束

- 唯一生产试点范围：目标年份 2027、北京、全日制、统考、计算机相关专业，处于候选名单收敛阶段。
- 冻结试点清单中的全部 10 个年度招生计划项目 ID。工程烟雾测试链路仅包含以下 3 项：
  - `ao_2027_bupt_081200_ft_unified_plan01`
  - `ao_2027_bit_085404_ft_unified_plan01`
  - `ao_2027_bjut_085410_ft_unified_plan01`
- 在具备已审核的 2027 年官方证据及完整已发布规则集之前，生产资格状态必须为 `needs_confirmation`；任何占位事实都不得转化为用户结论。
- 合成数据和历史参考数据必须携带明确的命名空间及 `reference_year`。合成的 `reference_year=2026` 测试数据仅供测试，不得进入生产序列化输出、覆盖率指标、推荐数量或面向用户的结论。
- AI 推荐、支付、付费排名、移动端页面、真实网站抓取及外部搜索引擎继续关闭。
- 公开页面不得暴露基础设施健康状态、环境名称、构建版本、内部审阅备注、令牌摘要、来源存储键或实现细节。
- 每项行为变更都从失败测试开始。先运行针对性测试，再实现功能，随后运行受影响的测试套件，最后执行仓库验证检查。
- OpenAPI 是接口契约的来源。重新生成 `packages/api-client`，不得手写重复的 TypeScript DTO。
- 保留用户现有文件和工作区中无关的改动。每项任务只提交自身涉及的文件。

## 任务 1：使当前 Windows 工作区的 Python 与 OpenAPI 工具链可移植

**文件：**

- 新增：`scripts/python-runtime.mjs`
- 新增：`scripts/python-runtime.test.mjs`
- 新增：`scripts/check-python.mjs`
- 修改：`scripts/generate-api.mjs`
- 修改：`package.json`
- 测试：`scripts/python-runtime.test.mjs`

### 步骤 1：编写运行时解析的失败测试

导出一个可注入文件系统及环境参数的纯解析函数，按以下优先级解析：

1. Windows 下使用 `services/api/.venv/Scripts/python.exe`，POSIX 下使用 `.venv/bin/python`。
2. 当 `uv` 可用时，使用 `uv run --project services/api python`。
3. 仅将 `python`/`python3` 作为最终兜底。

测试契约示例如下：

```js
test("prefers the repository virtualenv on Windows", () => {
  const runtime = resolvePythonRuntime({
    platform: "win32",
    root: "E:/GradMatch",
    exists: (candidate) => candidate.endsWith("services/api/.venv/Scripts/python.exe"),
    commandExists: () => false,
  });

  assert.deepEqual(runtime, {
    command: "E:/GradMatch/services/api/.venv/Scripts/python.exe",
    prefixArgs: [],
  });
});
```

运行：`node --test scripts/python-runtime.test.mjs`

预期：测试失败，因为解析函数尚不存在。

### 步骤 2：实现解析函数与共享命令执行器

`scripts/python-runtime.mjs` 必须导出：

```js
export function resolvePythonRuntime(options = {}) {}
export function runPython(args, options = {}) {}
```

使用 `spawnSync` 并继承标准输入输出，保留子进程退出码；仓库虚拟环境存在时，不得要求全局安装 `uv`。

### 步骤 3：让代码生成和 Python 检查共用运行时

- 修改 `scripts/generate-api.mjs`，通过 `runPython` 执行 `services/api/scripts/export_openapi.py`。
- 新增 `scripts/check-python.mjs`，在 `services/api` 目录执行以下命令：
  - `python -m pytest -p no:cacheprovider`
  - `python -m ruff check src tests`
  - `python -m pyright --pythonpath <resolved-python> src tests`
  - `python manage.py makemigrations --check --dry-run`，并设置 `DJANGO_SETTINGS_MODULE=gradmatch.config.settings_test`。
- 新增包脚本 `test:tooling` 和 `check:python`，将其纳入根目录 `test`/`check` 流程，避免重复执行。

### 步骤 4：验证并提交

运行：

```powershell
node --test scripts/python-runtime.test.mjs
pnpm check:python
pnpm check:api-drift
```

预期：即使本机全局 `python` 和 `uv` 不可用，全部检查仍能通过。

提交信息：`fix: make python tooling use project runtime`

## 任务 2：分离不可变原始数据块与每次来源访问记录

**文件：**

- 修改：`services/api/src/gradmatch/ingestion/models.py`
- 修改：`services/api/src/gradmatch/ingestion/admin.py`
- 修改：`services/api/src/gradmatch/ingestion/runner.py`
- 新增：`services/api/src/gradmatch/ingestion/migrations/0002_rawblob_sourcefetch.py`
- 修改：`services/api/tests/ingestion/test_runner.py`
- 新增：`services/api/tests/ingestion/test_models.py`

### 步骤 1：编写来源溯源的失败测试

定义两类独立记录：

```python
class RawBlob(models.Model):
    content_hash = models.CharField(max_length=64, unique=True)
    storage_key = models.CharField(max_length=512, unique=True)
    byte_size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SourceFetch(models.Model):
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT)
    run = models.ForeignKey(IngestionRun, on_delete=models.CASCADE, related_name="fetches")
    source_url = models.URLField(max_length=2048)
    requested_at = models.DateTimeField()
    fetched_at = models.DateTimeField(null=True, blank=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    etag = models.CharField(max_length=512, blank=True)
    last_modified = models.CharField(max_length=512, blank=True)
    status = models.CharField(max_length=24)
    blob = models.ForeignKey(RawBlob, null=True, on_delete=models.PROTECT)
    error_summary = models.TextField(blank=True)
```

测试必须证明：

- 两次成功抓取相同字节内容时，创建 1 条 `RawBlob` 和 2 条 `SourceFetch` 记录。
- 每次抓取保留 URL、运行记录、时间戳、状态和响应元数据。
- 访问失败时仍创建 `SourceFetch`，但不关联原始数据块。
- 删除旧表前，先迁移现有 `RawArtifact` 数据。

运行：`services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/ingestion -q`

预期：在当前单记录产物模型下测试失败。

### 步骤 2：实现模型结构、数据迁移与执行器行为

上传前计算原始字节的 SHA-256 哈希。哈希已存在时复用原始数据块记录和对象键，但每次都必须创建新的访问记录。不得将抓取的页面正文直接存入 PostgreSQL。

### 步骤 3：验证并提交

运行：

```powershell
services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/ingestion -q
pnpm check:python
```

提交信息：`feat: preserve source fetch provenance`

## 任务 3：新增冻结的试点目录和只读 API

**文件：**

- 新增：`services/api/src/gradmatch/catalog/__init__.py`
- 新增：`services/api/src/gradmatch/catalog/apps.py`
- 新增：`services/api/src/gradmatch/catalog/models.py`
- 新增：`services/api/src/gradmatch/catalog/admin.py`
- 新增：`services/api/src/gradmatch/catalog/api.py`
- 新增：`services/api/src/gradmatch/catalog/seed.py`
- 新增：`services/api/src/gradmatch/catalog/migrations/0001_initial.py`
- 新增：`services/api/src/gradmatch/catalog/migrations/0002_seed_pilot_manifest.py`
- 修改：`services/api/src/gradmatch/config/settings.py`
- 修改：`services/api/src/gradmatch/system/api.py`
- 新增：`services/api/tests/catalog/test_manifest.py`
- 新增：`services/api/tests/catalog/test_api.py`

### 步骤 1：编写清单与 API 的失败测试

建立以下契约：

```python
class CoverageManifest(models.Model):
    key = models.SlugField(unique=True)
    version = models.PositiveIntegerField()
    target_year = models.PositiveSmallIntegerField()
    scope = models.JSONField()
    frozen_at = models.DateTimeField()


class AnnualOffering(models.Model):
    id = models.CharField(primary_key=True, max_length=96)
    target_year = models.PositiveSmallIntegerField()
    institution = models.ForeignKey("Institution", on_delete=models.PROTECT)
    taxonomy_node = models.ForeignKey("TaxonomyNode", on_delete=models.PROTECT)
    title = models.CharField(max_length=256)
    degree_type = models.CharField(max_length=24)
    study_mode = models.CharField(max_length=24)
    admission_pathway = models.CharField(max_length=32)
    publication_status = models.CharField(max_length=32)
```

同时新增 `Institution`、`TaxonomyRevision`、`TaxonomyNode` 和有序的 `ManifestEntry(engineering_slice: bool)` 模型。

测试必须断言：

- 迁移准确写入 `pilot-scope-2027-v1.md` 中的 10 个 ID。
- 只有冻结的 3 个工程链路 ID 标记为 `engineering_slice=True`。
- 每个种子项目均为 `target_year=2027`、`full_time`、`unified_exam` 和 `pending_publication`。
- `GET /api/v1/pilot-scope`、`/taxonomy`、`/offerings` 和 `/offerings/{id}` 仅暴露公开目录字段。
- 筛选条件不能突破冻结清单范围。
- 不返回测试数据命名空间或 2026 年的值。

运行：`services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/catalog -q`

预期：测试失败，因为目录模块尚不存在。

### 步骤 2：实现模型结构、冻结数据迁移与路由

在现有 `/api/v1` Ninja API 下挂载目录路由。对不在当前生效清单中的 ID 返回 `404`，避免泄露目录记录是否存在。

### 步骤 3：验证并提交

运行：

```powershell
services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/catalog -q
pnpm check:python
```

提交信息：`feat: add frozen pilot catalog`

## 任务 4：新增可审核证据与确定性规则修订

**文件：**

- 新增：`services/api/src/gradmatch/advising/__init__.py`
- 新增：`services/api/src/gradmatch/advising/apps.py`
- 新增：`services/api/src/gradmatch/advising/models.py`
- 新增：`services/api/src/gradmatch/advising/publication.py`
- 新增：`services/api/src/gradmatch/advising/rules.py`
- 新增：`services/api/src/gradmatch/advising/admin.py`
- 新增：`services/api/src/gradmatch/advising/migrations/0001_initial.py`
- 修改：`services/api/src/gradmatch/config/settings.py`
- 新增：`services/api/tests/advising/test_publication.py`
- 新增：`services/api/tests/advising/test_rules.py`

### 步骤 1：编写发布边界的失败测试

为以下内容新增不可变或版本化记录：

- `SourceDocumentRevision`：关联 `SourceFetch`。
- `EvidenceClaimRevision`：关联一个招生项目及字段键。
- `ReviewDecision`：包含操作人、审核结果和备注。
- `PublicationEvent`：标识获得批准的确切证据声明修订版本。
- `RuleSetRevision`：包含命名空间（`production` 或 `test_fixture`）、目标年份、参考年份、发布状态和完整性标记。
- `EligibilityRule`：包含事实键、运算符（`equals`、`in`、`gte`、`is_true`）、预期 JSON 值、原因码和证据引用。
- `RuleEvidenceUsage`：将规则关联到其使用的确切证据声明修订版本。

测试必须证明：

- 未审核的证据声明不能发布。
- 合成来源不能发布到生产规则集中。
- `reference_year=2026` 的规则集不能使用生产命名空间。
- 2027 年生产规则至少需要一条已批准且已发布的 2027 年证据声明，才能成为当前生效规则。
- 已发布记录只允许追加；纠错必须创建新修订版本。

运行：`services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/advising/test_publication.py services/api/tests/advising/test_rules.py -q`

预期：测试失败，因为决策建议模块的发布能力尚不存在。

### 步骤 2：实现发布流程与测试数据防护

通过服务函数提供能力，不在模型层进行隐式修改：

```python
def publish_claim(*, claim_id: int, reviewer, now) -> PublicationEvent: ...
def publish_rule_set(*, rule_set_id: int, reviewer, now) -> RuleSetRevision: ...
def evaluate_rule(rule: EligibilityRule, facts: dict[str, object]) -> bool | None: ...
```

尽可能使用数据库约束，并在服务层原子事务中再次执行安全检查。

### 步骤 3：验证并提交

先运行针对性测试，再执行 `pnpm check:python`。

提交信息：`feat: add evidence and rule publication controls`

## 任务 5：实现事实集修订与资格三态

**文件：**

- 修改：`services/api/src/gradmatch/advising/models.py`
- 新增：`services/api/src/gradmatch/advising/eligibility.py`
- 新增：`services/api/src/gradmatch/advising/api.py`
- 新增：`services/api/src/gradmatch/advising/migrations/0002_fact_sets_eligibility.py`
- 修改：`services/api/src/gradmatch/system/api.py`
- 新增：`services/api/tests/advising/test_eligibility.py`
- 新增：`services/api/tests/advising/test_fact_set_api.py`

### 步骤 1：编写确定性评估的失败测试

新增：

```python
class FactSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class FactSetRevision(models.Model):
    fact_set = models.ForeignKey(FactSet, on_delete=models.CASCADE, related_name="revisions")
    version = models.PositiveIntegerField()
    confirmed_facts = models.JSONField()
    input_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class EligibilityAssessment(models.Model):
    offering = models.ForeignKey(AnnualOffering, on_delete=models.PROTECT)
    fact_revision = models.ForeignKey(FactSetRevision, on_delete=models.PROTECT)
    rule_set = models.ForeignKey(RuleSetRevision, null=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=32)
    reasons = models.JSONField()
    input_hash = models.CharField(max_length=64)
```

必须满足的行为：

- 完整且已发布的规则集中，只要有一条硬性规则被确认不满足，就返回 `ineligible`。
- 仅当每条适用的硬性规则均已确认且通过时，才返回 `eligible`。
- 存在缺失事实、缺失证据、不完整或未发布规则，以及当前全部生产种子项目时，返回 `needs_confirmation`。
- 相同的规范化输入产生相同的哈希和原因排序。
- 测试数据规则只能通过服务层显式设置 `allow_test_fixture=True` 传入；生产 API 绝不暴露该开关。
- API 端点 `POST /api/v1/fact-sets` 和 `POST /api/v1/eligibility-assessments` 拒绝未知事实键，并返回稳定原因码。

### 步骤 2：实现并验证

不持久化面向用户的文案；持久化稳定原因码和证据版本 ID。

运行：

```powershell
services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/advising/test_eligibility.py services/api/tests/advising/test_fact_set_api.py -q
pnpm check:python
```

提交信息：`feat: add deterministic eligibility assessments`

## 任务 6：新增版本化比较与访客决策快照

**文件：**

- 修改：`services/api/src/gradmatch/advising/models.py`
- 新增：`services/api/src/gradmatch/advising/comparison.py`
- 新增：`services/api/src/gradmatch/advising/capabilities.py`
- 修改：`services/api/src/gradmatch/advising/api.py`
- 新增：`services/api/src/gradmatch/advising/migrations/0003_comparisons_snapshots.py`
- 新增：`services/api/tests/advising/test_comparison.py`
- 新增：`services/api/tests/advising/test_guest_capability.py`
- 新增：`services/api/tests/advising/test_snapshot_api.py`

### 步骤 1：编写比较与安全性的失败测试

新增稳定的请求记录与不可变的结果修订版本：

- `GuestSession(token_digest, expires_at, owner, claimed_at)`：只存储令牌的 SHA-256 摘要。
- `ComparisonRun`：关联事实修订、冻结清单、所有者或访客会话。
- 比较结果模型：`ComparisonRunResult(version, result, result_hash, trigger_publication_event)`。
- `DecisionSnapshot`：关联确切的结果修订版本，并采用以下结局之一：
  - `shortlist_ready`
  - `no_suitable_offering`
  - `awaiting_official_information`
  - `postpone_application`

测试必须证明：

- 当前冻结试点产生 `awaiting_official_information`，不得生成虚构的候选名单。
- 排序和哈希必须具有确定性。
- `POST /comparison-runs`、`GET /comparison-runs/{id}`、`POST /decision-snapshots` 和 `GET /decision-snapshots/{id}` 强制执行所有权检查。
- 随机生成的 256 位访问能力令牌仅放在设置了 `Secure`、`HttpOnly`、`SameSite=Lax` 且短期过期的 Cookie 中；数据库只存储其摘要。
- 仅知道 UUID 不足以访问其他访客的快照。
- 通过 `POST /decision-snapshots/{id}/claim` 认领快照时，必须同时持有已认证会话和有效访问能力令牌，随后分配所有权，并撤销或轮换访客令牌。
- 过期或重放的访问能力令牌必须被拒绝。

### 步骤 2：实现并验证

使用 `secrets.token_urlsafe(32)`、`hmac.compare_digest` 和原子认领事务。不得序列化令牌摘要或内部结果输入。

先运行新增的决策建议模块测试，再执行 `pnpm check:python`。

提交信息：`feat: add secure guest decision snapshots`

## 任务 7：新增纠错、审计事件、事务发件箱发布与幂等重算

**文件：**

- 新增：`services/api/src/gradmatch/support/__init__.py`
- 新增：`services/api/src/gradmatch/support/apps.py`
- 新增：`services/api/src/gradmatch/support/models.py`
- 新增：`services/api/src/gradmatch/support/services.py`
- 新增：`services/api/src/gradmatch/support/tasks.py`
- 新增：`services/api/src/gradmatch/support/api.py`
- 新增：`services/api/src/gradmatch/support/admin.py`
- 新增：`services/api/src/gradmatch/support/migrations/0001_initial.py`
- 修改：`services/api/src/gradmatch/config/settings.py`
- 修改：`services/api/src/gradmatch/system/api.py`
- 新增：`services/api/tests/support/test_corrections.py`
- 新增：`services/api/tests/support/test_recomputation.py`

### 步骤 1：编写生命周期与幂等性的失败测试

模型：

- `CorrectionCase`：包含招生项目、字段键、建议来源 URL、说明、状态、提交人和时间戳。
- `AuditEvent`：只追加的操作人、动作和目标元数据。
- `OutboxEvent`：包含唯一事件键、载荷、发布时间和处理状态。
- `JobExecution`：通过唯一的 `(event_key, handler_name)` 保证幂等。
- `SnapshotUpdate`：将旧快照或结果关联到新计算结果，并保存稳定的差异载荷。

必须满足的行为：

- 匿名用户和已登录用户都可提交纠错，但不能查看审阅者备注。
- 只有工作人员可以审核、接受、发布或拒绝纠错。
- 接受纠错会创建新的证据修订；发布和创建事务发件箱事件在同一事务内完成。
- 同一事件处理两次，每个受影响的运行仍只创建 1 个新的 `ComparisonRunResult` 和 1 个 `SnapshotUpdate`。
- 原始快照和结果保持不可变且可读取。
- `POST /corrections` 和 `GET /corrections/{id}` 只暴露可安全提供给提交人的状态信息。

### 步骤 2：实现并验证

Celery 任务必须调用幂等业务处理器；测试同步调用该处理器。根据已持久化的证据版本引用选择受影响的运行，不进行全表重算。

先运行支持模块测试，再执行完整 Python 检查。

提交信息：`feat: add correction publication workflow`

## 任务 8：重新生成 API 客户端并提供平台无关业务契约

**文件：**

- 修改：`packages/api-client/src/generated/core.ts`
- 修改：`packages/api-client/src/core-client.ts`
- 修改：`packages/api-client/src/index.ts`
- 修改：`packages/domain/package.json`
- 新增：`packages/domain/src/pilot.ts`
- 新增：`packages/domain/src/decision.ts`
- 修改：`packages/domain/src/index.ts`
- 新增：`packages/domain/test/pilot.test.ts`
- 新增：`packages/domain/test/decision.test.ts`

### 步骤 1：编写跨平台契约的失败测试

业务模块只能依赖自动生成的 API 类型、Zod 和普通 TypeScript，不得导入 DOM、Next.js、React 或 React Native API。

测试覆盖：

- 解析公开的试点范围响应。
- 解析资格状态和全部四种决策结局。
- 拒绝非预期状态或泄露的内部字段。
- 原因码与公开文案之间的稳定映射；`needs_confirmation` 文案解释不确定性，不暗示已通过资格或被录取。

### 步骤 2：重新生成、实现并验证

运行：

```powershell
pnpm generate:api
pnpm --filter @gradmatch/domain test
pnpm typecheck
pnpm check:api-drift
```

提交信息：`feat: publish generated decision contracts`

## 任务 9：构建 Web 试点决策流程

**文件：**

- 编辑前阅读：`apps/web/node_modules/next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md`
- 编辑前阅读：`apps/web/node_modules/next/dist/docs` 下相关的 Next.js 表单与数据变更指南。
- 新增：`apps/web/app/match/page.tsx`
- 新增：`apps/web/app/match/loading.tsx`
- 新增：`apps/web/app/match/error.tsx`
- 新增：`apps/web/app/match/result/[id]/page.tsx`
- 新增：`apps/web/components/match/fact-form.tsx`
- 新增：`apps/web/components/match/offering-list.tsx`
- 新增：`apps/web/components/match/decision-summary.tsx`
- 新增：`apps/web/lib/pilot-api.ts`
- 修改：`apps/web/app/page.tsx`
- 修改：`apps/web/app/globals.css`
- 新增：`apps/web/test/match-page.test.tsx`
- 新增：`apps/web/test/fact-form.test.tsx`
- 新增：`apps/web/test/decision-summary.test.tsx`

### 步骤 1：编写用户流程的失败测试

测试用户可见的行为契约：

- 服务端渲染的 `/match` 页面通过生成客户端加载试点范围和招生项目。
- 表单只收集已确认且必要的事实，明确标注可选项和未知值。
- 提交后依次创建事实集修订、资格评估、比较和快照。
- 当前种子数据最终显示“等待 2027 官方信息”，并展示下一步行动和证据时效；不得展示排序推荐。
- 结果页呈现四种可能结局、原因码对应的通俗中文文案、来源与证据状态，以及纠错入口。
- 渲染内容中不得出现平台状态、环境、构建版本、存储键、审阅备注或令牌值。
- 在可行范围内，通过组件断言覆盖键盘焦点、标签、错误提示、对比度、减少动效偏好和移动端宽度布局。

### 步骤 2：以服务端优先渲染方式实现

目录加载保留在服务端组件中，仅将表单和交互式展开控件作为客户端组件。使用设计令牌及克制的动效，不新增重型动画库。

### 步骤 3：验证并提交

运行：

```powershell
pnpm --filter @gradmatch/web test
pnpm --filter @gradmatch/web typecheck
pnpm --filter @gradmatch/web build
```

提交信息：`feat: add pilot decision flow`

## 任务 10：验证纵向链路并记录本机原生运行方式

**文件：**

- 新增：`services/api/tests/e2e/test_pilot_vertical_slice.py`
- 新增：`scripts/native-status.mjs`
- 修改：`README.md`
- 修改：`.env.example`
- 修改：`docs/architecture.md`
- 修改：`docs/product-requirements.md`

### 步骤 1：编写端到端失败测试

测试必须在不访问外部网络的情况下执行以下流程：

1. 加载冻结试点清单。
2. 创建访客事实集。
3. 在当前生产数据下，将全部 3 个工程链路项目评估为 `needs_confirmation`。
4. 创建确定性比较和 `awaiting_official_information` 快照。
5. 使用已验证账户和访问能力令牌认领快照。
6. 提交基于本地测试来源的纠错，并由工作人员发布。
7. 对事务发件箱事件处理两次。
8. 断言只产生一次重算结果及更新、旧结果得到保留，且不存在测试数据泄露。

运行：`services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/e2e/test_pilot_vertical_slice.py -q`

预期：在全部环节完成集成前，测试失败。

### 步骤 2：新增原生运行诊断与文档

`scripts/native-status.mjs` 必须在不改变状态的前提下检查：

- 项目 Python 运行时和包导入。
- `DATABASE_URL` 指定的 PostgreSQL 是否可连接。
- `REDIS_URL` 指定的 Redis 是否可连接。
- 配置变量指定的 S3 兼容端点是否可连接。
- API/Web 端口是否已被占用。

记录 Windows 原生环境下 PostgreSQL、Redis、对象存储的前置准备，以及迁移、API、Celery worker/beat 和 Web 的启动命令。Docker Compose 保留为可选部署方式，不作为本地开发前提。

### 步骤 3：执行完整验证检查

运行：

```powershell
pnpm check
pnpm check:api-drift
pnpm --filter @gradmatch/web build
node scripts/native-status.mjs
```

如果已配置的原生服务可用，还应运行迁移并验证 `/api/v1/health/ready`；否则应报告具体不可用的依赖，不得宣称原生环境已就绪。

逐项对照全局约束完成最终需求评审，并在宣告完成前请求代码评审。

提交信息：`test: verify first pilot vertical slice`
