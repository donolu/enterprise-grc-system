"use client";
import { useState } from "react";
import { Form, Input, Button, Alert } from "antd";
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
    <Form layout="vertical" onFinish={onFinish} style={{ maxWidth: 360, margin: "10vh auto" }}>
      <h2>Sign in</h2>
      {error && <Alert type="error" message={error} style={{ marginBottom: 12 }} />}
      <Form.Item name="email" label="Email" rules={[{ required: true }, { type: "email" }]}>
        <Input />
      </Form.Item>
      <Form.Item name="password" label="Password" rules={[{ required: true }]}>
        <Input.Password />
      </Form.Item>
      <Form.Item name="otp" label="One-Time Code (if prompted)">
        <Input />
      </Form.Item>
      <Button type="primary" htmlType="submit" block>Login</Button>
    </Form>
  );
}
