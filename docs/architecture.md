# GradMatch 架构基线

**版本 1.3 | 更新于 2026-09-06**

## 目的与边界

GradMatch 起步采用以 Web 为先的模块化单体架构。`apps/web` 负责 Next.js 展示层；`services/api` 负责 Django 业务持久化、身份验证、管理、API 契约和后台采集。这一架构明确不采用微服务系统。

`packages/domain` 包含与平台无关的规则和查询定义。`packages/design-tokens` 仅包含语义化设计值。`packages/api-client` 根据 Django Ninja 和 allauth 的 OpenAPI 规范生成；浏览器、Web 服务器和未来的 Expo 应用使用这些客户端，而不是复制 DTO。

## 浏览器与 API 路径

浏览器通过单一 Caddy 源访问。`/api/*`、`/_allauth/*`、`/accounts/*`、`/admin/*`、`/static/*` 和 `/media/*` 路由到 Django。其余所有路径路由到 Next.js。浏览器请求始终使用相对于该源的路径，使 Django 无需配置 CORS 即可使用带有 Secure、HttpOnly、SameSite 属性的 cookie。服务器组件使用 `GRADMATCH_API_BASE_URL` 调用内部 API 服务。

身份验证采用 Django allauth Headless。浏览器使用会话 cookie；未来的移动应用使用 allauth `X-Session-Token`，不使用 JWT。电子邮箱验证为必需步骤，产品目前支持密码登录和一次性邮箱验证码登录。手机号、微信和 QQ 仅作为扩展边界。

所有能够调用改变状态的 Django 端点的浏览器客户端都使用相同的 CSRF 令牌和重试中间件；这一要求不限于 allauth 调用。公开的存活检查仅暴露粗粒度状态。依赖就绪状态、环境、构建以及模型/提供商详情仅限于内部运维路径，绝不在公开页面呈现。

## 后台数据边界

Celery worker 和 beat 共享 Django 代码库及 Redis 消息代理。当前的测试夹具适配器和 `RawArtifact` 模型属于基础代码，并非生产证据契约。在接入任何真实来源之前，必须迁移为使用 `RawBlob` 存储按内容寻址的字节数据，并使用 `SourceFetch` 记录每次访问尝试（来源、URL、请求/抓取时间、状态、ETag/Last-Modified、数据块和运行记录）。因此，两次相同的抓取会创建两条抓取记录和一个数据块。证据记录使用 `PROTECT` 或追加失效记录的方式，而非级联删除。

对象写入和数据库发布使用可恢复协议：暂存对象、验证哈希、提交引用和一条事务发件箱事件，然后以幂等方式完成最终处理/垃圾回收。抓取器强制执行主机白名单、DNS 解析后的私有地址/元数据地址拦截、重定向重新验证、响应大小/MIME/时间限制以及实际生效的速率限制。只有在记录权利依据、条款、展示范围及下架责任归属后，才启用来源访问。

## MVP 领域边界

现有的 `system`、`accounts` 和 `ingestion` 模块是已实现的基础。产品 PRD 在同一 Django 单体内新增以下模块；这些是模块边界，而非可独立部署的服务：

- `catalog`：覆盖清单、分类体系修订/节点/映射、院校、院系、专业、年度招生项目、计划观测记录、考试科目组合、费用概况、来源修订、证据主张、审核和发布工作流。
- `advising`：已确认的学习目标和版本化用户事实、硬约束、偏好因子定义、规则集修订、资格检查、比较运行/分组、决策快照、可选的推荐解释、使用关联和行动项。
- `outcomes`：指标定义、结构化证据范围、职业结果证据、职业、资格、专业到职业的关联，以及范围兼容性决策。
- `llm_gateway`：提供商适配器、结构化输出验证、证据绑定、成本/时间预算、审计元数据和安全回退。
- `support`：纠错工单、投诉、审核队列、发布事件、不可变审计事件，以及用户可见的工单状态。
- `commerce`：产品方案、订单、支付/退款、权益和商业实验。在满足策略层的放行/不放行前置条件之前，此边界中的真实支付保持禁用。
- `governance`：按能力范围划定的门禁决策和部署指纹。它不决定产品事实；它阻止在缺少当前有效且范围精确匹配的决策时启用外部研究、来源、AI、公开部署、支付或广告。

`catalog` 发布版本化招生证据。`outcomes` 发布版本化职业证据和范围决策，不修改 `catalog`。`advising` 是唯一允许计算三种资格状态和四个比较分组的模块。`llm_gateway` 可以解释 `advising` 的结果，但不能创建或覆盖事实、规则、资格状态、排序输入、职业指标或范围决策。`support` 可以提出变更，但只有相关发布工作流才能将证据设为当前有效版本。`commerce` 可以授予产品能力的访问权限，但不能写入目录事实、结果事实、资格、自然排序或推荐理由。在能力激活和部署启动时检查 `governance`；功能开关不能绕过它。

PostgreSQL 仍是权威数据源，足以支持试点的结构化搜索、规则、版本历史、事务发件箱和审计索引。Celery 通过 `JobExecution` 加幂等键处理采集、重新验证、受影响计划的重新计算、导出、删除和通知。对象存储保存相互隔离的不可变来源数据块，以及单独派生/脱敏的展示产物。Redis 仅用于临时数据，不能保存产品事实、事件或作业结果的唯一副本。MVP 不需要向量数据库、外部搜索服务、事件总线或微服务拆分。

## 决策与证据模型

目录层级采用版本化且可变的结构，而非强制使用一条固定链：

`CoverageManifest -> TaxonomyRevision -> TaxonomyNode(parent, level_type, code) -> AnnualOffering`

年度招生项目可以关联到官方一级学科、学位类别、专业领域或院校特定节点。`TaxonomyMapping` 记录旧/新节点、`mapped / ambiguous / unmapped / institution_specific`、生效日期、置信度和证据。历史招生项目保留其发布时所用的分类体系修订版本。2025 年的对应关系不得覆盖更早的代码，也不得暗示培养内容相同。

年度招生项目决策至少需要以下记录：

- `PlanObservation`：原始报告值、可选的派生值、计划阶段、报考途径、学习方式、专项/联合范围、分子/分母文本、证据和状态。各组成部分可能重叠或尚未公布，因此数据库不强制要求其总和等于已公布总数，也不暗中推导统考名额。
- `ExamSubjectBundle`：科目代码/名称、全国统一命题或院校自命题状态、适用性和变更事件。独立的可比性决策防止将不兼容科目组合的成绩放在一起排序。
- `ProgramCostProfile`：学制、每年/总学费、住宿可用性/费用、奖学金资格、校区、目标年份和证据状态。用户输入的生活成本和机会成本保留在 `advising` 中，不进入共享目录事实。
- `StudyGoal`、`PreferenceFactorDefinition` 和 `PreferenceProfile`：已确认的目标，以及版本化的因子含义、允许使用的证据、范围、未知情况处理方式和解释模板。最多三个因子且合计为 100 是一项 P1 实验；它绝不是获得安全结果的必要条件，历史调查百分比也绝不用于填充它。
- `SubjectMigrationAssessment`：已知匹配科目、新要求、未知项、加试以及绑定来源的推理。它不计算录取概率。

在这些记录中，空值一律表示未知。只有官方来源明确说明同一范围内的值为零时，才使用零。

证据图采用多对多关系，并记录修订版本：

`SourceDocumentRevision -> EvidenceClaimRevision -> ReviewDecision -> PublicationEvent`

`RuleEvidenceUsage`、`ComparisonRuleUsage` 和 `ComparisonEvidenceUsage` 将已发布的主张绑定到 `RuleSetRevision`、`EligibilityCheck`、`ComparisonRun` 和 `DecisionSnapshot`。可选的 AI 解释使用独立的 `RecommendationRuleUsage` 和 `RecommendationEvidenceUsage` 记录，引用不可变的比较运行。规则集包含适用性/覆盖清单；只有该清单完整且每项适用检查均通过时，才可能得到 `eligible_known`。任何未知规则、未知适用性、未知用户事实或来源冲突都会得到 `needs_confirmation`；任何已知且适用的检查失败都会得到 `ineligible_known`。

`DecisionSnapshot` 必须包含结果枚举：`shortlist_ready`、`no_suitable_offering`、`awaiting_official_information` 或 `postpone_application`。它记录保留、排除和暂缓的候选项、用户确认的理由、带原因代码的关键未知项、后续行动、回访日期、`comparison_run_id`、事实/规则/证据版本以及确定性结果哈希。它不存储标量置信度或录取概率；每个呈现的字段都带有其证据状态。重放相同的确定性输入必须复现资格、分组和顺序。可选的 LLM 文字说明不通过重新生成来证明相等；需保留原始响应、提示词模板版本、输入快照和验证结果。

访客比较运行和快照使用随机、短期有效且限定资源范围的能力令牌，通过带有 Secure、HttpOnly、SameSite 属性的 cookie 传递给浏览器；仅持久化其哈希。`POST /decision-snapshots/{id}/claim` 同时要求已认证会话和有效的访客能力凭证，然后原子性地分配所有权并轮换/撤销访客令牌。仅凭 ID 绝不授权读取或认领。

## 职业结果范围

职业证据不是 `Program` 上的属性列。它使用三种明确的记录：

- `MetricDefinition`：稳定键及版本、分子/分母定义、统计量（`rate`、`mean`、`median`、`p25`、`p75`）、单位、货币口径、观测窗口和纳入/排除规则。
- `EvidenceScope`：教育层次、学位类型、学习方式、分类体系修订/代码、院校/院系/专业、群组年份、毕业后时长、地区、行业、样本量、响应率和来源等级。
- `CareerOutcomeEvidence`：指标值、定义、范围、来源文档/主张、审核状态和可选的不确定性元数据。

`outcomes` 兼容性服务存储独立的 `entity_match`、`population_match`、`time_match`、`metric_match` 和 `mode_match` 决策，然后返回汇总结果 `exact_match`、`broader_context` 或 `incompatible`，以及规则版本和理由。只有汇总结果为 `exact_match` 时，才可标注为该专业的直接历史证据。`broader_context` 仅作为展示背景，绝不进入自然排序。`incompatible` 被排除在专业和比较 API 之外。

必须设置的防护包括：本科结果不能当作硕士结果；全行业工资不能当作毕业生起薪；全校比率不能当作专业比率；未分组或定义不同的学术型/专业型及全日制/非全日制样本不能用于比较这些群体；来源相同、群组相同、定义一致且充分分组的样本可以比较；均值和中位数不能互换。指标定义或范围规则变更会将受影响结果的重新计算加入队列，同时保留先前决策供审计。

`Occupation` 在可用时采用国家职业分类。`ProfessionalQualification` 记录准入类或水平评价类状态及证据。稳定性、工作强度、收入波动性、地域集中度、相关性和继续深造机会分别保留为独立观测项；不存在 `social_status_score` 字段。

## 商业隔离

首个软件商业假设是面向目标年份或申请季的决策套餐，不以永久订阅为假设。`commerce` 负责 `ProductOffer`、`Order`、`PaymentRecord`、`Refund`、`Entitlement` 和 `CommercialExperiment`。在主体、商户支付、订单、服务/退款、对账、开票、备案/许可和隐私前置条件通过策略门禁之前，真实支付提供商保持禁用。

权益可以控制深度比较限额、已保存计划容量、证据更新提醒或协作。权益不能作为目录发布、证据评级、结果范围、资格、自然排序或推荐理由的输入。advising API 绝不接收支付金额、赞助方身份或佣金作为排序特征。

免费权益始终允许完成一次安全决策闭环：资格、会改变结论的事实与未知项、官方来源、基础比较、一个决策快照，以及 S0/S1 纠错或资格失效通知。付费方案增加跨时间使用的便利性、历史记录、监控、协作、导出深度或 SLA；它们绝不用于解锁隐藏事实。商业关系也不能改变收录、更新优先级、证据展示位置或纠错优先级。

人工诊断服务与软件套餐使用独立的方案 ID 和账簿。每个群组记录实收收入、退款、支付手续费、直接审核/支持、模型/通知成本、付费获客、预先登记的关键申请节点事件和 D30 代理事件。数据运营工作日志记录录入、独立审核、返工、变更和支持耗时。报告展示交付贡献、扣除可归因获客成本后的贡献、扣除分摊的固定人力/合规/基础设施成本后的年度营业利润，以及 12 个月的逐月现金流。盈利门禁要求全年汇总的获客后贡献超过分摊固定成本；不能仅以收入作为分子。扩张还需检查当前六个月已承诺支出的流动性政策。激活成本不等于付费 CAC；不能根据人工服务收入推断软件盈利能力。

在产品方案具备版本化权益矩阵、交付边界、中断补偿、退款触发条件、责任分配、商户/订单/对账/开票就绪条件，以及适用的消费者保护/广告审查之前，支付保持禁用。`PaymentAttempt`、`Refund`、`EntitlementAdjustment` 和 `ExperimentExposure` 使用幂等键及可审计的状态转换。

## 本地开发与部署形态

首个产品实现切片明确排除 LLM、支付和移动端 UI。它使用[试点范围 V1](research/pilot-scope-2027-v1.md) 中冻结的三个计划年度招生项目 ID，并将每项尚未公布的 2027 年事实明确标记为待定，以验证：

`来源抓取 -> 原始数据块 -> 证据主张 -> 独立审核 -> 发布 -> 用户事实修订 -> 资格检查 -> 比较 -> 决策快照 -> 纠错 -> 新发布 -> 幂等重新计算 -> 用户可见差异`

在适用的 2027 年规则清单发布并经独立审核之前，这些计划标识对应的生产环境资格只能是 `needs_confirmation`。对 `eligible_known` 和 `ineligible_known` 的自动化覆盖使用非生产测试夹具命名空间，其中使用合成规则或带有 `reference_year=2026` 的历史快照；生产序列化器拒绝这些测试夹具，它们绝不计入清单覆盖，也不用于用户结论。

最小 API 集合为 `GET /pilot-scope`、`GET /taxonomy`、`GET /offerings`、`GET /offerings/{id}`、`POST /fact-sets`、`POST /eligibility-assessments`、`POST /comparison-runs`、`GET /comparison-runs/{id}`、`POST /decision-snapshots`、`GET /decision-snapshots/{id}`、`POST /decision-snapshots/{id}/claim`、`POST /corrections` 和 `GET /corrections/{id}`。比较运行以确定性方式计算资格、分组和顺序；快照选择一个结果，并冻结用户针对该次运行作出的决策。只有同一契约在[已冻结的十个招生项目清单](research/pilot-scope-2027-v1.md) 上通过验证后，才开始邀请。

首次邀请时，AI 端点、UI 和提供商调用通过功能开关禁用。只有在启用该能力之前，AI 要求才成为阻断条件；届时，结构化证据绑定、所有回退演练、标识/投诉机制以及匹配的 `GateDecision` 必须一并通过。

本地开发不要求 Docker。Web、Django、Celery worker/beat、PostgreSQL、兼容 Redis 的消息代理、兼容 S3 的对象存储和本地邮件捕获以原生进程或已安装的本地服务运行。工作区脚本应启动应用进程并执行依赖检查，不将持久化数据移回 C 盘。测试继续使用隔离的测试设置和本地测试夹具。

`scripts/native-status.mjs` 是原生环境的只读诊断入口：它检查 Python 包导入、PostgreSQL `SELECT 1`、Redis `PING`、S3 bucket 可访问性和 8000/3000 端口占用。依赖检查失败时命令以非零状态退出，但不会启动、停止或写入这些服务。数据库迁移、API、Celery worker、beat 和 Web 仍由开发者在独立终端显式启动。

### 首个纵向链路的已实现约束

截至 2026-09-06，工程链路使用冻结清单中的 3 个代表项目完成端到端自动化验收，同时保留邀请制前 10 项目的固定 `CoverageManifest` 分母。每个可发布规则集的全部 `RuleEvidenceUsage` 必须只引用同一个项目；生产资格选择同时要求精确匹配当前试点 manifest 和该项目的已发布证据，防止不同项目或不同 manifest 之间串用规则。

访客可以创建确认事实、资格检查、确定性比较和决策快照；认领快照同时要求已验证账户会话与对应能力凭证。纠错只有在工作人员接受并发布后才写入事务出箱；同一事件重复处理只创建一个 `JobExecution`、一个新比较结果版本和一个快照更新记录。旧比较结果与旧快照保持不可变。

端到端测试在同一测试数据库内主动放入 `synthetic`、`test_fixture` 和 `reference_year=2026` 数据，再验证公开响应不包含这些命名空间或内部对象存储字段。该测试不访问外部网络，也不证明 2027 招生事实已经发布。真实 PostgreSQL、Redis 与对象存储的本机可用性必须由当次原生诊断和就绪检查单独证明，不能由 SQLite 测试替代。

Docker Compose 仍是用于 CI 或未来服务器的可选、可复现的单机打包目标，并非本地功能开发的前置条件。在该打包模式下，PostgreSQL、Redis、MinIO 和 Mailpit 是内部依赖；一次性迁移服务是唯一执行迁移并收集静态资源的进程。Kubernetes、厂商专属部署服务、GraphQL 和外部搜索明确不在目标范围内。

## 试点运行预算

以下是邀请制试点的预算，并非对后续全国性服务的承诺：

- 搜索、详情和比较 API 的目标是在 30 名试点用户并发时，服务端耗时的第 95 百分位不超过 750 ms，不计外部文档抓取和 LLM 调用。
- 有证据支撑的页面必须在不使用 JavaScript 时仍可完成核心阅读；在试点数据集下，交互变更应在 100 ms 内显示进度，并在 2 秒内给出有用结果或明确的待处理状态。
- LLM 请求的软超时为 8 秒，硬超时为 15 秒。达到硬超时时，UI 转入基于已验证数据的回退流程，而非无限等待。
- PostgreSQL 和对象快照每天进行一次可恢复备份。邀请制试点的目标为 RPO 24 小时、RTO 4 小时；公开上线前必须进行一次恢复演练。
- 管理角色为 `viewer`、`editor`、`reviewer` 和 `administrator`。发布 P0 证据需要明确的审核操作，且该操作须区别于提取/编辑；所有发布、规则、纠错、导出和删除操作都需审计。
- 审计记录不包含原始对话文本和秘密信息，并受访问控制。网络日志、业务审计、行为分析、对话、订单和证据产物分别按用途设置保留期限；适用的法定最低期限优先于试点默认值，更长的保留期限必须记录其必要性。
- 健康状态和依赖详情仍仅供内部监控使用。公开错误使用经过脱敏的类别和不透露内部信息的事件 ID。

性能验收使用固定的数据集、端点组合、请求体、缓存状态、持续时间和评分脚本；仅有“30 名并发用户”并不是可复现的证据。在邀请用户之前，必须进行一次 PostgreSQL 加对象快照恢复演练，并达到规定的 RPO/RTO。

## 对外发布门禁

各项能力分别受独立门禁控制：

- 外部研究：告知/同意、退出与补偿、去标识化、保留期限和访问控制；
- 生产来源：权利/展示依据、条款/robots、爬虫安全、脱敏和下架；
- 外部 AI：提供商/处理者/子处理者、地区、保留期限/训练用途、自动化决策评估、显式/隐式标识，以及适用的备案/登记判定；
- 公开 Web 或应用：针对主体/域名/部署的备案或许可、安全定级/保护的适用性、隐私权利和事件响应；
- 支付或广告：商户、订单/合同、交付/退款、对账/开票、消费者保护、广告标识/文案和推荐证明审查。

每道门禁仅放行其指明的能力。18+ 的产品范围不会重新定义法定的儿童/未成年人规则。可关联的账户/会话标识符按去标识化个人信息处理，而非匿名数据。这些控制需要针对具体部署作出专业判定，并不主张所列的每项备案都适用于每种架构。

每个结果都是不可变的 `GateDecision(state, capability, scope, deployment_fingerprint, approver, evidence_ref, decided_at, expires_at, conditions, supersedes_id)`。`state` 为 `pending`、`go`、`conditional_go`、`not_applicable_with_rationale` 或 `no_go` 之一。只有能力和指纹精确匹配，且满足以下任一条件时才允许激活：当前决策为 `go`；`conditional_go` 中记录的所有条件均已验证；或已签署的 `not_applicable_with_rationale` 支持不适用结论。处于待定、不放行、已过期、条件未满足或指纹发生变化状态的部署默认被阻断。

## 移动端迁移路径

目前尚未构建 Expo UI。未来构建时，Expo/React Native 使用 `packages/domain`、`packages/design-tokens` 和 `packages/api-client`；平台专属组件保留在移动应用中。这使未来的 Android 和 iOS 开发无需重复定义请求类型、验证规则或产品语义。
