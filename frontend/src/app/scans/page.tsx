'use client'

import React from 'react'
import { Card, Typography, Space, Button } from 'antd'
import { RadarChartOutlined, PlusOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

export default function ScansPage() {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <RadarChartOutlined style={{ marginRight: 8 }} />
          Vulnerability Scanning
        </Title>
        <Text type="secondary">
          Monitor and manage security vulnerabilities across your infrastructure
        </Text>
      </div>

      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <RadarChartOutlined style={{ fontSize: '64px', color: '#1890ff', marginBottom: 16 }} />
          <Title level={3}>Vulnerability Management</Title>
          <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
            Import scan results from tools like OpenVAS and Nessus,
            track remediation progress, and manage security findings.
          </Text>
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