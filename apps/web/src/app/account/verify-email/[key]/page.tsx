import { EmailVerificationForm } from "../../../../features/auth/auth-forms";

type VerifyEmailPageProps = Readonly<{
  params: Promise<{ key: string }>;
}>;

export default async function VerifyEmailPage({ params }: VerifyEmailPageProps) {
  const { key } = await params;

  return (
    <>
      <p className="eyebrow">邮箱验证</p>
      <h1>确认这是你的邮箱</h1>
      <p>验证成功后即可选择密码或验证码登录。</p>
      <EmailVerificationForm initialKey={decodeURIComponent(key)} />
    </>
  );
}
