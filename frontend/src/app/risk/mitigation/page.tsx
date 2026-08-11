"use client";

import { Alert, Button, Card, Space } from "antd";
import { SafetyOutlined } from "@ant-design/icons";
import Link from "next/link";
import { Breadcrumb, PageHeader } from "@/components/ui";

export default function RiskMitigationPage() {
  return (
    <div>
      <Breadcrumb
        items={[
          { title: "Risk management", href: "/risk", icon: <SafetyOutlined /> },
          { title: "Risk treatment" },
        ]}
      />
      <PageHeader
        eyebrow="RISK & RESILIENCE"
        title="Risk treatment"
        description="Review and update treatment strategy and controls from each risk record."
        icon={<SafetyOutlined />}
        actions={<Button type="primary" href="/risk">Open risk register</Button>}
      />
      <Card style={{ maxWidth: 760 }}>
        <Space direction="vertical" size={20} style={{ width: "100%" }}>
          <Alert
            type="info"
            showIcon
            title="Action-plan workflow is being prepared"
            description="Granular treatment plans, owners and due-date tasks are not available yet. The previous screen displayed mock records and did not save changes, so it has been removed."
          />
          <Space wrap>
            <Button type="primary" href="/risk">Manage risk records</Button>
            <Link href="/analytics">Review risk analytics</Link>
          </Space>
        </Space>
      </Card>
    </div>
  );
}
