'use client'

import React from 'react'
import { Card, Space, Button } from 'antd'
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
            Import scan results from tools like OpenVAS and Nessus,
            track remediation progress, and manage security findings.
          </p>
          <Space>
            <Button type="primary" icon={<PlusOutlined />}>
              Import Scan Results
            </Button>
            <Button>
              View Vulnerabilities
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  )
}
