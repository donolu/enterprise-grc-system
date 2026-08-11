"use client";

import { useEffect, useState } from "react";
import { Alert, Button, Card, Form, Input, Spin, message } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { PageHeader } from "@/components/ui";
import api, { getErrorMessage } from "@/lib/api";

type Profile = {
  email: string;
  first_name: string;
  last_name: string;
};

export default function ProfilePage() {
  const [form] = Form.useForm<Profile>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void api.get<Profile>("/auth/profile/")
      .then(({ data }) => form.setFieldsValue(data))
      .catch((requestError: unknown) => setError(getErrorMessage(requestError)))
      .finally(() => setLoading(false));
  }, [form]);

  const saveProfile = async (values: Profile) => {
    setSaving(true);
    setError("");
    try {
      const { data } = await api.patch<Profile>("/auth/profile/", values);
      form.setFieldsValue(data);
      message.success("Profile updated");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="ACCOUNT"
        title="Profile settings"
        description="Keep your personal details accurate for assignment and audit records."
        icon={<UserOutlined />}
      />
      <Card style={{ maxWidth: 640 }}>
        {error && <Alert type="error" showIcon title="Profile could not be updated" description={error} style={{ marginBottom: 16 }} />}
        {loading ? <Spin /> : (
          <Form form={form} layout="vertical" onFinish={saveProfile}>
            <Form.Item label="Work email" name="email">
              <Input disabled />
            </Form.Item>
            <Form.Item label="First name" name="first_name" rules={[{ required: true, message: "Enter your first name" }]}>
              <Input autoComplete="given-name" />
            </Form.Item>
            <Form.Item label="Last name" name="last_name" rules={[{ required: true, message: "Enter your last name" }]}>
              <Input autoComplete="family-name" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={saving}>Save changes</Button>
          </Form>
        )}
      </Card>
    </div>
  );
}
