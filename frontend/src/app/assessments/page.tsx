'use client'

import React from 'react'
import { Alert, Button, Card, Space } from 'antd'
import { CheckSquareOutlined, DatabaseOutlined } from '@ant-design/icons'
import Link from 'next/link'
import { PageHeader } from '@/components/ui'

export default function AssessmentsPage() {
  return (
    <div>
      <PageHeader
        eyebrow="ASSURANCE PROGRAMME"
        title="Compliance assessments"
        description="Control assessments become available after a framework catalogue has been imported."
        icon={<CheckSquareOutlined />}
        actions={<Button type="primary" icon={<DatabaseOutlined />} href="/admin">Import a framework</Button>}
      />

      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <CheckSquareOutlined style={{ fontSize: '64px', color: '#1890ff', marginBottom: 16 }} />
          <h2>Prepare your assessment catalogue</h2>
          <p style={{ display: 'block', marginBottom: 24 }}>
            Import an approved framework pack to create the controls your team will assess.
          </p>
          <Alert
            type="info"
            showIcon
            title="Assessment setup is catalogue-led"
            description="The previous assessment wizard only simulated a completed assessment and did not create an auditable control assessment. It is unavailable until the real workflow is connected."
            style={{ maxWidth: 640, margin: '0 auto 24px', textAlign: 'left' }}
          />
          <Space>
            <Button type="primary" icon={<DatabaseOutlined />} href="/admin">Import framework catalogue</Button>
            <Link href="/policies/dashboard">Review policy readiness</Link>
          </Space>
        </div>
      </Card>
    </div>
  )
}
