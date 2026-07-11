'use client'

import React from 'react'
import { Card, Typography, Space, Button } from 'antd'
import { CheckSquareOutlined, PlusOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

export default function AssessmentsPage() {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <CheckSquareOutlined style={{ marginRight: 8 }} />
          Compliance Assessments
        </Title>
        <Text type="secondary">
          Conduct and track compliance assessments across frameworks
        </Text>
      </div>

      <Card>
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <CheckSquareOutlined style={{ fontSize: '64px', color: '#1890ff', marginBottom: 16 }} />
          <Title level={3}>Compliance Assessment Center</Title>
          <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
            Manage compliance assessments for various frameworks including
            SOC 2, ISO 27001, NIST CSF, and custom organizational standards.
          </Text>
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