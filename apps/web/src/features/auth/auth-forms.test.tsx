import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const transports = vi.hoisted(() => ({
  auth: {
    DELETE: vi.fn(),
    GET: vi.fn(),
    POST: vi.fn(),
  },
  core: {
    GET: vi.fn(),
  },
}));

vi.mock("../../lib/api-client", () => ({
  browserAuthClient: transports.auth,
  browserCoreClient: transports.core,
}));

import { AccountPanel } from "../account/account-panel";
import {
  EmailVerificationForm,
  LogoutButton,
  OneTimeCodeForm,
  PasswordLoginForm,
  SignupForm,
} from "./auth-forms";

function renderWithQuery(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function authenticatedResponse(status = 200) {
  return {
    data: {
      data: {
        user: { email: "student@example.test", id: 7 },
      },
      meta: { is_authenticated: true, session_token: "session-token" },
      status,
    },
    response: new Response(null, { status }),
  };
}

describe("authentication forms", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // biome-ignore lint/suspicious/noDocumentCookie: the browser authentication flow reads Django's CSRF cookie.
    document.cookie = "csrftoken=; Max-Age=0; path=/";
    transports.auth.GET.mockResolvedValue({ response: new Response(null, { status: 200 }) });
  });

  it("validates signup input before sending a request", async () => {
    const user = userEvent.setup();
    renderWithQuery(<SignupForm />);

    await user.click(screen.getByRole("button", { name: "创建账户" }));

    expect(await screen.findByText("请输入有效邮箱地址")).toBeInTheDocument();
    expect(transports.auth.POST).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("密码"), "1234567");
    await user.click(screen.getByRole("button", { name: "创建账户" }));
    expect(await screen.findByText("密码至少需要 8 个字符")).toBeInTheDocument();
  });

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

  it("submits signup with the generated allauth request shape and renders the pending state", async () => {
    transports.auth.POST.mockResolvedValueOnce(authenticatedResponse(401));
    const user = userEvent.setup();
    renderWithQuery(<SignupForm />);

    await user.type(screen.getByLabelText("邮箱"), "student@example.test");
    await user.type(screen.getByLabelText("密码"), "strong-password-123");
    await user.click(screen.getByRole("button", { name: "创建账户" }));

    await waitFor(() => {
      expect(transports.auth.GET).toHaveBeenCalledWith("/_allauth/{client}/v1/config", {
        params: { path: { client: "browser" } },
      });
      expect(transports.auth.POST).toHaveBeenCalledWith("/_allauth/{client}/v1/auth/signup", {
        body: { email: "student@example.test", password: "strong-password-123" },
        params: { path: { client: "browser" } },
      });
    });
    const configCallOrder = transports.auth.GET.mock.invocationCallOrder[0];
    const signupCallOrder = transports.auth.POST.mock.invocationCallOrder[0];
    if (configCallOrder === undefined || signupCallOrder === undefined) {
      throw new Error("Expected authentication initialization and signup calls.");
    }
    expect(configCallOrder).toBeLessThan(signupCallOrder);
    expect(screen.getByText("验证邮件已发送，请完成邮箱验证。")).toBeInTheDocument();
  });

  it("skips authentication initialization when the CSRF cookie already exists", async () => {
    // biome-ignore lint/suspicious/noDocumentCookie: the browser authentication flow reads Django's CSRF cookie.
    document.cookie = "csrftoken=existing-token; path=/";
    transports.auth.POST.mockResolvedValueOnce(authenticatedResponse(401));
    const user = userEvent.setup();
    renderWithQuery(<SignupForm />);

    await user.type(screen.getByLabelText("邮箱"), "student@example.test");
    await user.type(screen.getByLabelText("密码"), "strong-password-123");
    await user.click(screen.getByRole("button", { name: "创建账户" }));

    await waitFor(() => expect(transports.auth.POST).toHaveBeenCalled());
    expect(transports.auth.GET).not.toHaveBeenCalled();
  });

  it("deduplicates concurrent authentication initialization", async () => {
    let resolveConfig: ((result: { response: Response }) => void) | undefined;
    const configResponse = new Promise<{ response: Response }>((resolve) => {
      resolveConfig = resolve;
    });
    transports.auth.GET.mockReturnValueOnce(configResponse);
    transports.auth.POST.mockResolvedValue(authenticatedResponse(401));
    const user = userEvent.setup();
    renderWithQuery(
      <>
        <SignupForm />
        <PasswordLoginForm />
      </>,
    );
    const [firstEmail, secondEmail] = screen.getAllByLabelText("邮箱");
    const [firstPassword, secondPassword] = screen.getAllByLabelText("密码", { exact: true });
    const signupButton = screen.getByRole("button", { name: "创建账户" });
    const loginButton = screen.getByRole("button", { name: "密码登录" });
    if (!firstEmail || !firstPassword || !secondEmail || !secondPassword) {
      throw new Error("Expected signup and login form inputs.");
    }

    await user.type(firstEmail, "first@example.test");
    await user.type(firstPassword, "strong-password-123");
    await user.type(secondEmail, "second@example.test");
    await user.type(secondPassword, "strong-password-123");
    await user.click(signupButton);
    await user.click(loginButton);

    expect(transports.auth.GET).toHaveBeenCalledTimes(1);
    if (!resolveConfig) throw new Error("Expected authentication initialization to start.");
    resolveConfig({ response: new Response(null, { status: 200 }) });
    await waitFor(() => expect(transports.auth.POST).toHaveBeenCalledTimes(2));
  });

  it("submits password login and shows a server failure", async () => {
    transports.auth.POST.mockResolvedValueOnce({
      error: { status: 500 },
      response: new Response(null, { status: 500 }),
    });
    const user = userEvent.setup();
    renderWithQuery(<PasswordLoginForm />);

    await user.type(screen.getByLabelText("邮箱"), "student@example.test");
    await user.type(screen.getByLabelText("密码"), "strong-password-123");
    await user.click(screen.getByRole("button", { name: "密码登录" }));

    expect(await screen.findByText("请求未完成，请稍后重试。")).toBeInTheDocument();
    expect(transports.auth.POST).toHaveBeenCalledWith("/_allauth/{client}/v1/auth/login", {
      body: { email: "student@example.test", password: "strong-password-123" },
      params: { path: { client: "browser" } },
    });
  });

  it("requests and confirms a one-time code with the correct request shapes", async () => {
    transports.auth.POST.mockResolvedValueOnce(authenticatedResponse(401)).mockResolvedValueOnce(
      authenticatedResponse(200),
    );
    const user = userEvent.setup();
    renderWithQuery(<OneTimeCodeForm />);

    await user.type(screen.getByLabelText("邮箱"), "student@example.test");
    await user.click(screen.getByRole("button", { name: "发送登录验证码" }));
    expect(await screen.findByLabelText("验证码")).toBeInTheDocument();

    await user.type(screen.getByLabelText("验证码"), "ABCD-EFGH");
    await user.click(screen.getByRole("button", { name: "确认登录" }));

    expect(transports.auth.POST).toHaveBeenNthCalledWith(
      1,
      "/_allauth/{client}/v1/auth/code/request",
      { body: { email: "student@example.test" }, params: { path: { client: "browser" } } },
    );
    expect(transports.auth.POST).toHaveBeenNthCalledWith(
      2,
      "/_allauth/{client}/v1/auth/code/confirm",
      { body: { code: "ABCD-EFGH" }, params: { path: { client: "browser" } } },
    );
    expect(screen.getByText("登录成功。")).toBeInTheDocument();
  });

  it("confirms an email verification key", async () => {
    transports.auth.POST.mockResolvedValueOnce(authenticatedResponse(401));
    renderWithQuery(<EmailVerificationForm initialKey="verification-key" />);

    fireEvent.click(screen.getByRole("button", { name: "确认邮箱" }));

    await waitFor(() => {
      expect(transports.auth.POST).toHaveBeenCalledWith("/_allauth/{client}/v1/auth/email/verify", {
        body: { key: "verification-key" },
        params: { path: { client: "browser" } },
      });
    });
    expect(screen.getByText("邮箱已验证，现在可以登录。")).toBeInTheDocument();
  });

  it("treats the generated unauthenticated response as a successful logout", async () => {
    transports.auth.DELETE.mockResolvedValueOnce({ response: new Response(null, { status: 401 }) });
    const user = userEvent.setup();
    renderWithQuery(<LogoutButton />);

    await user.click(screen.getByRole("button", { name: "退出登录" }));

    await waitFor(() => {
      expect(transports.auth.DELETE).toHaveBeenCalledWith("/_allauth/{client}/v1/auth/session", {
        params: { path: { client: "browser" } },
      });
    });
    expect(screen.getByText("你已安全退出。")).toBeInTheDocument();
  });

  it("renders the authenticated account email from the generated core client", async () => {
    transports.core.GET.mockResolvedValueOnce({
      data: { email: "student@example.test", id: 7 },
      response: new Response(null, { status: 200 }),
    });
    renderWithQuery(<AccountPanel />);

    expect(await screen.findByText("student@example.test")).toBeInTheDocument();
    expect(transports.core.GET).toHaveBeenCalledWith("/api/v1/me");
  });
});
