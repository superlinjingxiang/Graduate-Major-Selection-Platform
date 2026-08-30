# Account and Homepage Adjustments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make password registration easier to use and keep internal platform health information off the public homepage.

**Architecture:** Django remains the authoritative password-policy layer through its standard password validator, while the React form mirrors the same minimum length before it submits. The existing client-side form gets a small, accessible password-visibility control; the public home route stops loading and rendering status presentation while the health endpoints remain available to infrastructure.

**Tech Stack:** Django 5.2, django-allauth Headless, Next.js App Router, React 19, React Hook Form, Zod, Vitest, Testing Library, Playwright.

**Spec:** `docs/product-requirements.md`

## Global Constraints

- 注册和密码登录流程的最低密码长度统一为 8 个字符。
- 注册密码默认隐藏；按钮只切换显示状态，不清空内容或改变输入焦点。
- 公开首页不得显示服务健康、依赖连接、部署环境或构建版本。
- `/api/v1/health/*` 与内部状态模块保留，不能因隐藏公开卡片而删除。
- 不新增 UI 依赖；图标使用本地 SVG 标记。

---

### Task 1: Enforce the eight-character password policy on the API

**Files:**

- Modify: `services/api/src/gradmatch/config/settings.py`
- Modify: `services/api/tests/test_authentication.py`

**Interfaces:**

- Consumes: django-allauth browser signup endpoint at `/_allauth/browser/v1/auth/signup`.
- Produces: Django `AUTH_PASSWORD_VALIDATORS` with `MinimumLengthValidator` configured as `min_length: 8`.

- [ ] **Step 1: Write the failing API-policy tests**

  Add these tests near the existing signup coverage:

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

- [ ] **Step 2: Run the two tests and verify RED**

  Run:

  ```powershell
  python -m uv --directory services/api run pytest tests/test_authentication.py -k "password_policy_requires or shorter_than_eight" -v
  ```

  Expected: the policy assertion fails because no password validators are configured; the seven-character signup is not rejected by the server.

- [ ] **Step 3: Configure the minimal Django validator**

  Add this setting directly after the allauth account configuration in `settings.py`:

  ```python
  AUTH_PASSWORD_VALIDATORS = [
      {
          "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
          "OPTIONS": {"min_length": 8},
      }
  ]
  ```

- [ ] **Step 4: Run the targeted API tests and verify GREEN**

  Run the Step 2 command. Expected: both tests pass.

- [ ] **Step 5: Run the complete authentication test module**

  Run:

  ```powershell
  python -m uv --directory services/api run pytest tests/test_authentication.py -v
  ```

  Expected: all authentication tests pass.

- [ ] **Step 6: Commit the API policy change**

  ```powershell
  git add services/api/src/gradmatch/config/settings.py services/api/tests/test_authentication.py
  git commit -m "feat: relax password policy to eight characters"
  ```

### Task 2: Add the accessible registration password-visibility control

**Files:**

- Modify: `apps/web/src/features/auth/auth-forms.tsx`
- Modify: `apps/web/src/features/auth/auth-forms.test.tsx`
- Modify: `apps/web/src/app/globals.css`

**Interfaces:**

- Consumes: the existing `FormField` and React Hook Form registration props.
- Produces: an optional `showPasswordToggle` field behavior with button labels `显示密码` and `隐藏密码`.

- [ ] **Step 1: Write failing form tests**

  Add tests that assert the registration form accepts exactly eight characters and that the toggle preserves the entered value:

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

  Add a seven-character validation assertion to the existing validation test:

  ```tsx
  await user.type(screen.getByLabelText("密码"), "1234567");
  await user.click(screen.getByRole("button", { name: "创建账户" }));
  expect(await screen.findByText("密码至少需要 8 个字符")).toBeInTheDocument();
  ```

- [ ] **Step 2: Run the form test file and verify RED**

  Run:

  ```powershell
  pnpm --filter @gradmatch/web test -- auth-forms.test.tsx
  ```

  Expected: the eight-character case is blocked by the 12-character schema and no `显示密码` button exists.

- [ ] **Step 3: Implement the smallest reusable field change**

  In `auth-forms.tsx`, change the Zod password rule to:

  ```tsx
  password: z.string().min(8, "密码至少需要 8 个字符"),
  ```

  Extend `FormField` with `showPasswordToggle?: boolean`. When it is true, keep a local `isPasswordVisible` state, use `type={isPasswordVisible ? "text" : "password"}`, and render a `type="button"` control beside the input. Its `aria-label` must switch between `显示密码` and `隐藏密码`; give its inline SVG `aria-hidden="true"`. Pass `showPasswordToggle` only from `SignupForm`.

  Add scoped CSS:

  ```css
  .input-with-action { position: relative; }
  .input-with-action .input { padding-right: 3.25rem; }
  .password-toggle { align-items: center; background: transparent; border: 0; color: var(--gm-text-muted); cursor: pointer; display: inline-flex; height: 2.5rem; justify-content: center; position: absolute; right: 0.2rem; top: 0.175rem; width: 2.5rem; }
  .password-toggle:hover { color: var(--gm-brand); }
  .password-toggle svg { height: 1.15rem; width: 1.15rem; }
  ```

- [ ] **Step 4: Run the form test file and verify GREEN**

  Run the Step 2 command. Expected: the new UI and validation tests pass alongside the existing request-shape tests.

- [ ] **Step 5: Run the complete web unit-test suite**

  Run:

  ```powershell
  pnpm --filter @gradmatch/web test
  ```

  Expected: all Vitest tests pass.

- [ ] **Step 6: Commit the registration UX change**

  ```powershell
  git add apps/web/src/features/auth/auth-forms.tsx apps/web/src/features/auth/auth-forms.test.tsx apps/web/src/app/globals.css
  git commit -m "feat: improve signup password entry"
  ```

### Task 3: Remove operational status from the public homepage

**Files:**

- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/e2e/authentication.spec.ts`

**Interfaces:**

- Consumes: the existing public route `/` and the Caddy-served browser application.
- Produces: a public homepage without `StatusPanel` or `loadServerStatus` usage; health endpoints and their implementation remain unchanged.

- [ ] **Step 1: Write the failing homepage end-to-end assertion**

  Replace the status-focused homepage test with:

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

- [ ] **Step 2: Run the homepage test and verify RED**

  Run:

  ```powershell
  pnpm e2e -- --grep "product homepage"
  ```

  Expected: the test fails because the current homepage renders the platform-status card and `development` metadata.

- [ ] **Step 3: Remove only the public status presentation**

  In `page.tsx`, remove the imports for `loadServerStatus` and `StatusPanel`, remove `export const dynamic = "force-dynamic"`, remove `const presentation = await loadServerStatus()`, and remove `<StatusPanel presentation={presentation} />` from the hero section. Leave `features/status`, health API routes, and their tests in place for internal operations.

- [ ] **Step 4: Run the homepage end-to-end test and verify GREEN**

  Run the Step 2 command. Expected: the public page displays the product entry content and none of the operational text.

- [ ] **Step 5: Run full regression checks**

  Run:

  ```powershell
  pnpm check
  python -m uv --directory services/api run ruff check .
  python -m uv --directory services/api run pyright
  python -m uv --directory services/api run pytest
  pnpm e2e
  ```

  Expected: every command exits with code 0.

- [ ] **Step 6: Commit the public-homepage change**

  ```powershell
  git add apps/web/src/app/page.tsx apps/web/e2e/authentication.spec.ts
  git commit -m "feat: hide operational details from homepage"
  ```
