'use client'

import React from 'react'
import { Card, Space, Button } from 'antd'
import { CheckSquareOutlined, PlusOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/ui'

export default function AssessmentsPage() {
  return (
    <div>
      <PageHeader eyebrow="ASSURANCE PROGRAMME" title="Compliance assessments" description="Conduct and track compliance assessments across frameworks." icon={<CheckSquareOutlined />} actions={<Button type="primary" icon={<PlusOutlined />}>Start assessment</Button>} />

      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <CheckSquareOutlined style={{ fontSize: '64px', color: '#1890ff', marginBottom: 16 }} />
          <h2>Compliance Assessment Center</h2>
          <p style={{ display: 'block', marginBottom: 24 }}>
            Manage compliance assessments for various frameworks including
            SOC 2, ISO 27001, NIST CSF, and custom organizational standards.
          </p>
          <Space>
            <Button type="primary" icon={<PlusOutlined />}>
              Start Assessment
            </Button>
            <Button>
              View All Assessments
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  )
}
