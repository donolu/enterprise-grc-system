"use client";
import { useState } from "react";
import { Form, Input, Button, Alert } from "antd";
import { ArrowRightOutlined, LockOutlined, MailOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { login } from "@/lib/auth";
import { useRouter } from "next/navigation";

function safeNext(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return "/";
  }
  return value;
}

type LoginFormValues = {
  email: string;
  password: string;
  otp?: string;
};

export default function LoginPage() {
  const [error, setError] = useState<string|null>(null);
  const router = useRouter();

  const onFinish = async (values: LoginFormValues) => {
    try {
      setError(null);
      await login(values.email, values.password, values.otp);
      const next = new URLSearchParams(window.location.search).get("next");
      router.push(safeNext(next));
    } catch (e) {
      if (e instanceof Error) {
        setError(e.message || "Login failed");
      } else {
        setError("An unexpected error occurred during login.");
      }
    }
  };

  return (
    <Form layout="vertical" onFinish={onFinish} className="auth-form">
      <div className="auth-form-heading">
        <span className="auth-form-icon"><SafetyCertificateOutlined /></span>
        <span className="auth-form-kicker">Member access</span>
        <h2 aria-label="Sign in">Welcome back</h2>
        <p>Sign in to continue to your control centre.</p>
      </div>
      {error && <Alert type="error" title={error} showIcon style={{ marginBottom: 20 }} />}
      <Form.Item name="email" label="Work email" rules={[{ required: true }, { type: "email" }]}>
        <Input size="large" prefix={<MailOutlined />} autoComplete="email" />
      </Form.Item>
      <Form.Item name="password" label="Password" rules={[{ required: true }]}>
        <Input.Password size="large" prefix={<LockOutlined />} autoComplete="current-password" />
      </Form.Item>
      <Form.Item name="otp" label="Authenticator code (if prompted)">
        <Input size="large" inputMode="numeric" autoComplete="one-time-code" />
      </Form.Item>
      <Button type="primary" htmlType="submit" block size="large" aria-label="Login" icon={<ArrowRightOutlined />} iconPlacement="end">Continue securely</Button>
      <p className="auth-form-note">Access is protected with two-factor authentication where enabled.</p>
    </Form>
  );
}
