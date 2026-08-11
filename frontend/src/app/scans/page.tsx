'use client'

import React from 'react'
import { Alert, Card, Space, Button } from 'antd'
import { RadarChartOutlined, PlusOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/ui'

export default function ScansPage() {
  return (
    <div>
      <PageHeader
        eyebrow="SECURITY OPERATIONS"
        title="Vulnerability scanning"
        description="Monitor and manage security vulnerabilities across your infrastructure."
        icon={<RadarChartOutlined />}
      />

      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <RadarChartOutlined style={{ fontSize: '64px', color: '#1890ff', marginBottom: 16 }} />
          <h2>Vulnerability management</h2>
          <p style={{ color: 'var(--ink-soft, #466166)', display: 'block', marginBottom: 24 }}>
            Scanner connections are not configured for this tenant yet. Vulnerability workflows will become available once an integration is enabled.
          </p>
          <Alert
            type="info"
            showIcon
            title="Scanner integration required"
            description="Configure an approved scanner connection before importing findings or viewing vulnerability records."
            style={{ maxWidth: 640, margin: '0 auto 24px', textAlign: 'left' }}
          />
          <Space>
            <Button type="primary" icon={<PlusOutlined />} disabled>
              Import Scan Results
            </Button>
            <Button disabled>
              View Vulnerabilities
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  )
}
