# 账户与首页调整实施计划

> **致执行代理：** 必需的子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐项任务实施本计划。步骤使用复选框（`- [ ]`）语法跟踪。

**目标：** 提升密码注册的易用性，并使公开首页不再展示平台内部健康信息。

**架构：** Django 继续通过其标准密码验证器作为密码策略的权威层，React 表单则在提交前执行相同的最小长度校验。在现有客户端表单中加入一个小型、支持无障碍访问的密码可见性控件；公开首页路由停止加载和渲染状态展示内容，健康检查端点仍供基础设施使用。

**技术栈：** Django 5.2、django-allauth Headless、Next.js App Router、React 19、React Hook Form、Zod、Vitest、Testing Library、Playwright。

**规格说明：** `docs/product-requirements.md`

## 全局约束

- 注册和密码登录流程的最低密码长度统一为 8 个字符。
- 注册密码默认隐藏；按钮只切换显示状态，不清空内容或改变输入焦点。
- 公开首页不得显示服务健康、依赖连接、部署环境或构建版本。
- `/api/v1/health/*` 与内部状态模块保留，不能因隐藏公开卡片而删除。
- 不新增 UI 依赖；图标使用本地 SVG 标记。

---

### 任务 1：在 API 中执行八字符密码策略

**文件：**

- 修改：`services/api/src/gradmatch/config/settings.py`
- 修改：`services/api/tests/test_authentication.py`

**接口：**

- 使用：位于 `/_allauth/browser/v1/auth/signup` 的 django-allauth 浏览器注册端点。
- 产出：Django `AUTH_PASSWORD_VALIDATORS`，其中 `MinimumLengthValidator` 配置为 `min_length: 8`。

- [ ] **步骤 1：编写预期失败的 API 策略测试**

  在现有注册测试附近添加以下测试：

  ```python
  def test_password_policy_requires_at_least_eight_characters() -> None:
      assert settings.AUTH_PASSWORD_VALIDATORS == [
          {
              "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
              "OPTIONS": {"min_length": 8},
          }
      ]


  @pytest.mark.django_db
  def test_signup_rejects_a_password_shorter_than_eight_characters(client: Client) -> None:
      response = client.post(
          "/_allauth/browser/v1/auth/signup",
          data=json.dumps({"email": "short@example.test", "password": "1234567"}),
          content_type="application/json",
      )

      assert response.status_code == 400
      assert "8" in str(response.json())
  ```

- [ ] **步骤 2：运行这两个测试并确认失败**

  运行：

  ```powershell
  python -m uv --directory services/api run pytest tests/test_authentication.py -k "password_policy_requires or shorter_than_eight" -v
  ```

  预期：由于未配置密码验证器，策略断言失败；服务器未拒绝使用七字符密码的注册请求。

- [ ] **步骤 3：配置最小的 Django 验证器**

  在 `settings.py` 中的 allauth 账户配置后紧接着添加以下设置：

  ```python
  AUTH_PASSWORD_VALIDATORS = [
      {
          "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
          "OPTIONS": {"min_length": 8},
      }
  ]
  ```

- [ ] **步骤 4：运行针对性的 API 测试并确认通过**

  运行步骤 2 中的命令。预期：两个测试均通过。

- [ ] **步骤 5：运行完整的认证测试模块**

  运行：

  ```powershell
  python -m uv --directory services/api run pytest tests/test_authentication.py -v
  ```

  预期：所有认证测试均通过。

- [ ] **步骤 6：提交 API 策略变更**

  ```powershell
  git add services/api/src/gradmatch/config/settings.py services/api/tests/test_authentication.py
  git commit -m "feat: relax password policy to eight characters"
  ```

### 任务 2：添加支持无障碍访问的注册密码可见性控件

**文件：**

- 修改：`apps/web/src/features/auth/auth-forms.tsx`
- 修改：`apps/web/src/features/auth/auth-forms.test.tsx`
- 修改：`apps/web/src/app/globals.css`

**接口：**

- 使用：现有的 `FormField` 和 React Hook Form 注册属性。
- 产出：可选的 `showPasswordToggle` 字段行为，按钮标签为 `显示密码` 和 `隐藏密码`。

- [ ] **步骤 1：编写预期失败的表单测试**

  添加测试，断言注册表单接受恰好八个字符的密码，且切换可见性时保留已输入的值：

  ```tsx
  it("accepts an eight-character signup password", async () => {
    transports.auth.POST.mockResolvedValueOnce(authenticatedResponse(401));
    const user = userEvent.setup();
    renderWithQuery(<SignupForm />);

    await user.type(screen.getByLabelText("邮箱"), "student@example.test");
    await user.type(screen.getByLabelText("密码"), "12345678");
    await user.click(screen.getByRole("button", { name: "创建账户" }));

    await waitFor(() => expect(transports.auth.POST).toHaveBeenCalled());
  });

  it("reveals and re-hides the signup password without changing it", async () => {
    const user = userEvent.setup();
    renderWithQuery(<SignupForm />);
    const password = screen.getByLabelText("密码");

    await user.type(password, "12345678");
    expect(password).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "显示密码" }));
    expect(password).toHaveAttribute("type", "text");
    expect(password).toHaveValue("12345678");
    expect(screen.getByRole("button", { name: "隐藏密码" })).toBeInTheDocument();
  });
  ```

  在现有验证测试中添加七字符密码的校验断言：

  ```tsx
  await user.type(screen.getByLabelText("密码"), "1234567");
  await user.click(screen.getByRole("button", { name: "创建账户" }));
  expect(await screen.findByText("密码至少需要 8 个字符")).toBeInTheDocument();
  ```

- [ ] **步骤 2：运行表单测试文件并确认失败**

  运行：

  ```powershell
  pnpm --filter @gradmatch/web test -- auth-forms.test.tsx
  ```

  预期：八字符用例被要求 12 个字符的校验模式拦截，且不存在 `显示密码` 按钮。

- [ ] **步骤 3：实现最小的可复用字段变更**

  在 `auth-forms.tsx` 中，将 Zod 密码规则改为：

  ```tsx
  password: z.string().min(8, "密码至少需要 8 个字符"),
  ```

  为 `FormField` 扩展 `showPasswordToggle?: boolean`。当其为真时，维护本地 `isPasswordVisible` 状态，使用 `type={isPasswordVisible ? "text" : "password"}`，并在输入框旁渲染一个 `type="button"` 控件。其 `aria-label` 必须在 `显示密码` 和 `隐藏密码` 之间切换；为其内联 SVG 设置 `aria-hidden="true"`。仅从 `SignupForm` 传入 `showPasswordToggle`。

  添加限定作用范围的 CSS：

  ```css
  .input-with-action { position: relative; }
  .input-with-action .input { padding-right: 3.25rem; }
  .password-toggle { align-items: center; background: transparent; border: 0; color: var(--gm-text-muted); cursor: pointer; display: inline-flex; height: 2.5rem; justify-content: center; position: absolute; right: 0.2rem; top: 0.175rem; width: 2.5rem; }
  .password-toggle:hover { color: var(--gm-brand); }
  .password-toggle svg { height: 1.15rem; width: 1.15rem; }
  ```

- [ ] **步骤 4：运行表单测试文件并确认通过**

  运行步骤 2 中的命令。预期：新增的 UI 和校验测试以及现有的请求结构测试均通过。

- [ ] **步骤 5：运行完整的 Web 单元测试套件**

  运行：

  ```powershell
  pnpm --filter @gradmatch/web test
  ```

  预期：所有 Vitest 测试均通过。

- [ ] **步骤 6：提交注册用户体验变更**

  ```powershell
  git add apps/web/src/features/auth/auth-forms.tsx apps/web/src/features/auth/auth-forms.test.tsx apps/web/src/app/globals.css
  git commit -m "feat: improve signup password entry"
  ```

### 任务 3：从公开首页移除运行状态

**文件：**

- 修改：`apps/web/src/app/page.tsx`
- 修改：`apps/web/e2e/authentication.spec.ts`

**接口：**

- 使用：现有的公开路由 `/` 和由 Caddy 提供服务的浏览器应用。
- 产出：不使用 `StatusPanel` 或 `loadServerStatus` 的公开首页；健康检查端点及其实现保持不变。

- [ ] **步骤 1：编写预期失败的首页端到端断言**

  将以状态为重点的首页测试替换为：

  ```tsx
  test("renders a product homepage without operational details", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "把复杂选择，变成更笃定的下一步。" })).toBeVisible();
    await expect(page.getByRole("link", { name: "创建账户" })).toBeVisible();
    await expect(page.getByText("平台状态")).toHaveCount(0);
    await expect(page.getByText("服务已准备就绪")).toHaveCount(0);
    await expect(page.getByText("development", { exact: true })).toHaveCount(0);
  });
  ```

- [ ] **步骤 2：运行首页测试并确认失败**

  运行：

  ```powershell
  pnpm e2e -- --grep "product homepage"
  ```

  预期：由于当前首页渲染了平台状态卡片和 `development` 元数据，测试失败。

- [ ] **步骤 3：仅移除公开状态展示**

  在 `page.tsx` 中，移除 `loadServerStatus` 和 `StatusPanel` 的导入，移除 `export const dynamic = "force-dynamic"`，移除 `const presentation = await loadServerStatus()`，并从首屏主视觉区域移除 `<StatusPanel presentation={presentation} />`。保留 `features/status`、健康检查 API 路由及其测试，供内部运维使用。

- [ ] **步骤 4：运行首页端到端测试并确认通过**

  运行步骤 2 中的命令。预期：公开页面显示产品入口内容，不显示任何运维文字。

- [ ] **步骤 5：运行完整的回归检查**

  运行：

  ```powershell
  pnpm check
  python -m uv --directory services/api run ruff check .
  python -m uv --directory services/api run pyright
  python -m uv --directory services/api run pytest
  pnpm e2e
  ```

  预期：每条命令均以退出码 0 结束。

- [ ] **步骤 6：提交公开首页变更**

  ```powershell
  git add apps/web/src/app/page.tsx apps/web/e2e/authentication.spec.ts
  git commit -m "feat: hide operational details from homepage"
  ```
