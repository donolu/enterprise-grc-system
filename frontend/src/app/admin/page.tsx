'use client'

import React from 'react'
import { Card, Typography, Space, Button, Row, Col } from 'antd'
import { SettingOutlined, UserOutlined, DatabaseOutlined, KeyOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

export default function AdminPage() {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <SettingOutlined style={{ marginRight: 8 }} />
          System Administration
        </Title>
        <Text type="secondary">
          Manage system settings, users, and configuration
        </Text>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ textAlign: 'center' }}>
            <UserOutlined style={{ fontSize: '32px', color: '#1890ff', marginBottom: 16 }} />
            <Title level={4}>User Management</Title>
            <Text type="secondary">
              Manage user accounts, roles, and permissions
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ textAlign: 'center' }}>
            <DatabaseOutlined style={{ fontSize: '32px', color: '#52c41a', marginBottom: 16 }} />
            <Title level={4}>Data Management</Title>
            <Text type="secondary">
              Configure frameworks, controls, and system data
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ textAlign: 'center' }}>
            <KeyOutlined style={{ fontSize: '32px', color: '#faad14', marginBottom: 16 }} />
            <Title level={4}>Access Control</Title>
            <Text type="secondary">
              Manage API keys, authentication, and security settings
            </Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable style={{ textAlign: 'center' }}>
            <SettingOutlined style={{ fontSize: '32px', color: '#f5222d', marginBottom: 16 }} />
            <Title level={4}>System Settings</Title>
            <Text type="secondary">
              Configure global settings, notifications, and integrations
            </Text>
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 24 }}>
        <div style={{ textAlign: 'center', padding: '30px 0' }}>
          <SettingOutlined style={{ fontSize: '48px', color: '#1890ff', marginBottom: 16 }} />
          <Title level={3}>Administration Dashboard</Title>
          <Text type="secondary">
            Welcome to the GRC Suite administration panel. Use the cards above to navigate to different administrative functions.
          </Text>
        </div>
      </Card>
    </div>
  )
}