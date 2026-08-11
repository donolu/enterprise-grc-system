"use client";

import { Alert, Button, Card, Space } from "antd";
import { CheckSquareOutlined, DatabaseOutlined } from "@ant-design/icons";
import Link from "next/link";
import { Breadcrumb, PageHeader } from "@/components/ui";

export default function CreateAssessmentPage() {
  return (
    <div>
      <Breadcrumb
        items={[
          { title: "Assessments", href: "/assessments" },
          { title: "Assessment setup" },
        ]}
      />
      <PageHeader
        eyebrow="ASSURANCE PROGRAMME"
        title="Assessment setup"
        description="Control assessments are created from an imported framework catalogue."
        icon={<CheckSquareOutlined />}
        actions={<Button type="primary" icon={<DatabaseOutlined />} href="/admin">Import a framework</Button>}
      />
      <Card style={{ maxWidth: 760 }}>
        <Space direction="vertical" size={20} style={{ width: "100%" }}>
          <Alert
            type="info"
            showIcon
            title="A framework catalogue is required"
            description="The previous form only simulated a completed assessment and did not create an auditable control assessment. Import a framework pack first, then use its controls to begin the real workflow."
          />
          <Space wrap>
            <Button type="primary" icon={<DatabaseOutlined />} href="/admin">Open catalogue import</Button>
            <Link href="/assessments">Return to assessments</Link>
          </Space>
        </Space>
      </Card>
    </div>
  );
}
