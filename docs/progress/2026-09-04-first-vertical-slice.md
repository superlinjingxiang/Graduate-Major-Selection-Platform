# GradMatch 阶段进度记录 — 2026-09-04

## 当前结论

本次按用户要求暂停功能开发，保存进度并提交、推送 `dev` 分支。这是开发检查点（WIP），不是可发布版本，也不代表当前目标完成。

[首个纵向链路计划](../superpowers/plans/2026-09-02-first-vertical-slice.md)的任务 1–8 已有代码和分阶段提交；任务 9 仅新增前端测试草稿及共享包依赖，页面和组件尚未实现；任务 10 的端到端、本机原生集成与最终验收尚未完成。当前 Web 测试和类型检查不通过，不能标记全仓检查通过。

本次记录前的代码基线为 `3194ced`。本检查点另外保存三个 Web 测试文件、`apps/web/package.json`、对应 lockfile 和进度文档；没有继续实现新功能。

## 产品目标与边界

- 产品面向研究生考试择校、择专业决策，商业目标是盈利；目前实现的是可信决策基础链路，尚未证明付费需求、转化率或盈利能力。
- 唯一生产试点范围：2027 年、北京、全日制、统考、计算机相关专业、候选名单收敛阶段；冻结清单包含 10 个计划项目，不代表已有 10 个完整有效的招生结论。
- 首个工程链路只处理以下 3 个计划项目：
  - `ao_2027_bupt_081200_ft_unified_plan01`：北京邮电大学，081200。
  - `ao_2027_bit_085404_ft_unified_plan01`：北京理工大学，085404。
  - `ao_2027_bjut_085410_ft_unified_plan01`：北京工业大学，085410。
- 仓库内生产种子数据仍为 `pending_publication`。尚未导入并审核真实 2027 年官方证据及完整规则，当前应返回 `needs_confirmation`，决策快照为 `awaiting_official_information`。这是本项目的数据状态，不是对所有学校实际发布情况的断言。
- `synthetic` / `test_fixture`、`reference_year=2026` 数据仅用于测试，不能进入生产结论或覆盖率口径。
- AI、支付、付费排名、移动端产品页面、真实网站采集继续关闭；移动端复用通过平台无关共享包保留。
- 用户页面不展示基础设施健康、环境、构建版本、存储路径、审阅备注和令牌信息。
- 本机开发方向已改为原生启动后端与数据库等依赖；Docker Compose 保留为可选部署路径，不作为当前本机开发前提。

## 已落地代码

以下状态表示代码及相应单元测试已落地，不表示跨服务集成与发布验收完成。

| 计划任务 | 已落地内容 | 提交 |
| --- | --- | --- |
| 1. Python 工具链 | 项目虚拟环境优先、统一 Python 检查与 OpenAPI 生成运行时、Pyright 解释器路径修正 | `0e64db3`、`ed0b3f9` |
| 2. 来源溯源 | `RawBlob` 按哈希去重，`SourceFetch` 独立记录每次访问、响应元数据与失败记录，旧数据迁移 | `c6da1a7` |
| 3. 试点目录 | 冻结清单、目录迁移与种子数据、pilot-scope / taxonomy / offerings 只读接口 | `0d24d32` |
| 4. 证据与规则发布 | 不可变证据修订、审核记录、发布事件、规则版本、生产与测试数据隔离 | `81ef12c` |
| 5. 资格三态 | 不可变事实版本、确定性哈希、资格评估与原因码、缺失证据保守处理 | `9bcf2c5` |
| 6. 比较与访客快照 | 比较结果版本、四种决策结局、访客 capability Cookie、所有权检查、已验证账户认领 | `fce91ea` |
| 7. 纠错与重算 | 纠错状态流转、staff 服务层权限、审计、事务 outbox、幂等重算处理器、旧快照保留 | `7190758` |
| 8. 共享契约 | 生成 core 客户端、保留 auth 客户端、Zod 校验与中文原因文案、跨平台契约测试 | `3194ced` |

纠错发布后会创建需要重新审核的规则版本（`coverage_complete=False`），受影响结果回到待确认状态，不自动从新证据推断资格条件。Celery 任务入口已存在，但 outbox 自动派发仍待接通。

## 正在进行与未完成工作

### 任务 9：Web 决策流程 — 测试草稿阶段

已新增：

- `apps/web/src/features/match/match-page.test.tsx`：试点范围和项目展示、不泄露运行信息。
- `apps/web/src/features/match/fact-form.test.tsx`：确认范围、提交事实、三次资格评估、比较与快照的调用顺序。
- `apps/web/src/features/match/decision-summary.test.tsx`：等待官方信息的结论、原因和纠错入口。
- Web 对 `@gradmatch/domain` 的 workspace 依赖及 lockfile 条目；本机链接已存在。

尚未实现 `/match`、`/match/result/[id]`、事实表单、结果摘要、公共目录加载、加载/错误状态、纠错交互及首页入口调整。测试草稿本身也需要随实现完善，不能作为完整验收覆盖。

计划中的 Web 文件路径应以现有结构为准：路由位于 `apps/web/src/app`，业务组件位于 `apps/web/src/features/match`，辅助取数模块位于 `apps/web/src/lib`。

### 任务 10：完整集成与原生运行 — 未完成

- 还没有首个纵向链路端到端测试或 `scripts/native-status.mjs`。
- 尚未完成本机 PostgreSQL、Redis、S3 兼容存储、邮件、Celery 与 Web/API 的联合验收。
- 现有 Next 配置没有本机同源 API/auth 转发；访客 Cookie 路径为 `/api/v1`，结果页还需设计同源客户端读取，不能假定 Next 页面请求能读取该 Cookie。
- 尚未补齐原生启动说明、浏览器端验收、完整构建检查和最终代码评审。

## 本次检查结果

执行时间：2026-09-04，本机 Windows。以下均为本次实际执行结果；未用此前通过的结果代替本次状态。

| 检查 | 命令与工作目录 | 结果 |
| --- | --- | --- |
| Python 全套检查 | 仓库根目录：`node scripts/check-python.mjs` | 93 项测试通过；Ruff 通过；Pyright 0 错误、0 警告；无新增迁移差异 |
| Domain 测试 | `packages/domain`：`.\node_modules\.bin\vitest.CMD run` | 2 个文件、7 项测试通过 |
| Domain 类型 | 仓库根目录：`.\node_modules\.bin\tsc.CMD -p packages/domain/tsconfig.json --noEmit` | 通过 |
| API 客户端契约 | 仓库根目录：`.\node_modules\.bin\tsc.CMD -p packages/api-client/tsconfig.contract.json` | 通过 |
| OpenAPI 漂移 | 仓库根目录：`node scripts/check-api-drift.mjs` | 两套客户端重新生成，无契约差异 |
| Web 测试 | `apps/web`：`.\node_modules\.bin\vitest.CMD run` | 既有 2 个测试文件的 13 项测试通过；新增 3 个测试文件在导入阶段失败，对应实现不存在 |
| Web TypeScript | `apps/web`：`..\..\node_modules\.bin\tsc.CMD -p tsconfig.json --noEmit` | 3 个 TS2307 错误，均为缺少上述页面/组件模块 |
| 完整构建、`pnpm check`、浏览器 E2E、本机服务就绪 | 本次未运行 | 不作通过声明 |

Python 测试使用 `settings_test`：SQLite 内存数据库、内存邮件与同步 Celery。它们证明单元/服务层行为，不证明真实 PostgreSQL 事务、Redis 队列或对象存储集成可用。

## 恢复开发时优先处理

1. 先复核规则与单个招生项目的绑定：当前生产规则选择经 manifest 关联项目，需要增加“同一清单内不同项目不能误用彼此规则”的回归测试。
2. 复核匿名连续创建事实集的会话行为：当前每次创建新访客会话并覆盖 Cookie，可能导致旧快照失去访问能力。
3. 用真实 PostgreSQL 验证纠错发布中的锁查询（包含 `select_for_update()` 与 `distinct()`），同时验证事务/重试；SQLite 测试不覆盖这类数据库差异。
4. 补齐 outbox 自动派发、重试和运行验证；目前只有处理器及 Celery 任务入口，不能宣称纠错发布后会自动完成后台重算。
5. 实现任务 9 并使现有红色测试转绿，补充异常/权限/可访问性场景，验证原生同源认证与访客流程。
6. 完成任务 10、Web 构建和全仓检查，更新需求/架构/启动说明，最终评审后再判断纵向链路是否完成。
7. 依照既定验证协议继续验证用户价值与付费意愿；本次工程进度不作为盈利可行性证明，也不提前接通真实支付。

## 保存边界

仅提交项目进度与本轮任务文件。`.env`、本机运行数据、`.local-runtime/`、`.idea/` 以及无关的自动生成 `apps/web/AGENTS.md`、`apps/web/CLAUDE.md` 不纳入本次提交。不删除数据库，不强制推送，不将当前目标标记为完成。
