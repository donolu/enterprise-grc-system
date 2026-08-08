"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  Row,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import {
  CheckCircleOutlined,
  MailOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
} from "@ant-design/icons";
import { getErrorMessage } from "@/lib/api";
import {
  getTenantEmailSettings,
  requestTenantEmailVerification,
  updateTenantEmailSettings,
} from "@/lib/services/tenantEmailService";

const { Title, Text } = Typography;

export default function TenantEmailSettings() {
  const [form] = Form.useForm();
  const [settings, setSettings] = useState<Awaited<ReturnType<typeof getTenantEmailSettings>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);

  const loadSettings = useCallback(async () => {
    try {
      const data = await getTenantEmailSettings();
      setSettings(data);
      form.setFieldsValue({
        email_sender_name: data.email_sender_name,
        email_sender_address: data.email_sender_address,
        email_reply_to: data.email_reply_to,
      });
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [form]);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const saveSettings = async (values: Record<string, string>) => {
    setSaving(true);
    try {
      const data = await updateTenantEmailSettings(values);
      setSettings(data);
      message.success("Email identity settings saved");
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const sendVerification = async () => {
    setSending(true);
    try {
      const response = await requestTenantEmailVerification();
      message.success(
        `Verification email sent. It expires ${new Date(response.expires_at ?? "").toLocaleString()}.`,
      );
      await loadSettings();
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setSending(false);
    }
  };

  if (!settings && !loading) {
    return (
      <Alert
        type="error"
        showIcon
        message="Email identity settings are unavailable"
        description="Your account may not have tenant administrator access."
      />
    );
  }

  const verified = Boolean(settings?.sender_email_verified);

  return (
    <Space direction="vertical" size={24} style={{ width: "100%" }}>
      <div>
        <Text type="secondary">Tenant administration / outbound communications</Text>
        <Title level={2} style={{ margin: "6px 0 0" }}>
          Email identity
        </Title>
        <Text type="secondary">
          Control how Provena identifies your organisation in tenant notifications.
        </Text>
      </div>

      <Row gutter={[20, 20]}>
        <Col xs={24} lg={15}>
          <Card loading={loading} title={<Space><MailOutlined /> Sender details</Space>}>
            <Form form={form} layout="vertical" onFinish={saveSettings} requiredMark="optional">
              <Form.Item
                label="Sender name"
                name="email_sender_name"
                rules={[{ max: 255, message: "Use 255 characters or fewer." }]}
              >
                <Input placeholder="Acme Corporation" />
              </Form.Item>
              <Form.Item
                label="Sender email address"
                name="email_sender_address"
                rules={[{ type: "email", message: "Enter a valid email address." }]}
                extra="A new address must be verified before it is used for tenant mail."
              >
                <Input placeholder="notifications@acme.example" />
              </Form.Item>
              <Form.Item
                label="Reply-to address"
                name="email_reply_to"
                rules={[{ type: "email", message: "Enter a valid email address." }]}
              >
                <Input placeholder="support@acme.example" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={saving}>
                Save settings
              </Button>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={9}>
          <Card title={<Space><SafetyCertificateOutlined /> Verification</Space>}>
            <Space direction="vertical" size={16} style={{ width: "100%" }}>
              <div>
                {verified ? (
                  <Tag color="success" icon={<CheckCircleOutlined />}>Verified sender</Tag>
                ) : (
                  <Tag color="warning">Verification required</Tag>
                )}
              </div>
              <Descriptions size="small" column={1}>
                <Descriptions.Item label="Address">
                  {settings?.email_sender_address || "Not configured"}
                </Descriptions.Item>
                <Descriptions.Item label="Verified at">
                  {settings?.sender_email_verified_at
                    ? new Date(settings.sender_email_verified_at).toLocaleString()
                    : "Not yet verified"}
                </Descriptions.Item>
              </Descriptions>
              <Alert
                type={verified ? "success" : "info"}
                showIcon
                message={verified ? "Ready for tenant notifications" : "Confirm the sender address"}
                description={
                  verified
                    ? "The configured address has confirmed ownership."
                    : "We will email a one-time confirmation link to the configured sender address."
                }
              />
              <Button
                block
                icon={<SendOutlined />}
                onClick={() => void sendVerification()}
                loading={sending}
                disabled={!settings?.email_sender_address}
              >
                {verified ? "Send verification again" : "Send verification email"}
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
