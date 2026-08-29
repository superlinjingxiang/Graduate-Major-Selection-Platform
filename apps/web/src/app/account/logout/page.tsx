import { LogoutButton } from "../../../features/auth/auth-forms";

export default function LogoutPage() {
  return (
    <>
      <p className="eyebrow">账户安全</p>
      <h1>退出当前会话</h1>
      <p>退出后，可以随时通过密码或邮箱验证码再次登录。</p>
      <LogoutButton />
    </>
  );
}
