'use client'

import React, { useState } from 'react'
import { Card, Typography, Space, Button, Table, Tag, Progress, Row, Col, Modal, Descriptions, Divider, Form, Input, Select, message } from 'antd'
import { SafetyOutlined, ArrowLeftOutlined, CheckCircleOutlined, ClockCircleOutlined, EyeOutlined, EditOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import { Breadcrumb, StatusTag, PriorityTag } from '@/components/ui'

const { Title, Text } = Typography

export default function RiskMitigationPage() {
  const router = useRouter()
  const [selectedRisk, setSelectedRisk] = useState<any>(null)
  const [isViewModalVisible, setIsViewModalVisible] = useState(false)
  const [isEditModalVisible, setIsEditModalVisible] = useState(false)
  const [editForm] = Form.useForm()

  // Mock mitigation plan data with detailed risk information
  const mitigationPlans = [
    {
      id: 1,
      riskId: 'RISK-2024-0001',
      riskTitle: 'Data Breach from Third-Party Vendor',
      strategy: 'Mitigate',
      status: 'in_progress',
      owner: 'John Smith',
      ownerEmail: 'john.smith@company.com',
      progress: 65,
      dueDate: '2024-12-31',
      priority: 'high',
      description: 'Potential data breach risk from third-party vendor integration lacking proper security controls.',
      riskLevel: 'high',
      impact: 4,
      likelihood: 3,
      category: 'Cybersecurity',
      treatmentPlan: 'Implement additional security controls including vendor security assessments, data encryption, and monitoring.',
      currentControls: 'Basic vendor security questionnaire in place.',
      actions: [
        { task: 'Vendor Security Assessment', status: 'completed', dueDate: '2024-10-15' },
        { task: 'Implement Data Encryption', status: 'in_progress', dueDate: '2024-11-30' },
        { task: 'Setup Monitoring Alerts', status: 'pending', dueDate: '2024-12-15' }
      ]
    },
    {
      id: 2,
      riskId: 'RISK-2024-0002',
      riskTitle: 'GDPR Compliance Violation',
      strategy: 'Mitigate',
      status: 'completed',
      owner: 'Sarah Johnson',
      ownerEmail: 'sarah.johnson@company.com',
      progress: 100,
      dueDate: '2024-11-15',
      priority: 'medium',
      description: 'Risk of non-compliance with GDPR regulations due to inadequate data processing procedures.',
      riskLevel: 'medium',
      impact: 5,
      likelihood: 2,
      category: 'Compliance',
      treatmentPlan: 'Update privacy policies, implement data mapping, and conduct staff training on GDPR requirements.',
      currentControls: 'Basic privacy policy in place, data handling procedures documented.',
      actions: [
        { task: 'Update Privacy Policies', status: 'completed', dueDate: '2024-09-30' },
        { task: 'Data Mapping Exercise', status: 'completed', dueDate: '2024-10-15' },
        { task: 'Staff GDPR Training', status: 'completed', dueDate: '2024-11-01' }
      ]
    }
  ]

  const columns = [
    {
      title: 'Risk ID',
      dataIndex: 'riskId',
      key: 'riskId',
      render: (text: string, record: any) => (
        <Button
          type="link"
          style={{ padding: 0, height: 'auto' }}
          onClick={() => handleViewRisk(record)}
        >
          <Text strong style={{ color: '#2F6FED' }}>{text}</Text>
        </Button>
      )
    },
    {
      title: 'Risk Title',
      dataIndex: 'riskTitle',
      key: 'riskTitle',
    },
    {
      title: 'Strategy',
      dataIndex: 'strategy',
      key: 'strategy',
      render: (strategy: string) => <Tag color="blue">{strategy}</Tag>
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <StatusTag status={status} context="risk" />
    },
    {
      title: 'Owner',
      dataIndex: 'owner',
      key: 'owner',
    },
    {
      title: 'Progress',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => (
        <Space direction="vertical" size={2}>
          <Progress
            percent={progress}

            status={progress === 100 ? 'success' : progress > 80 ? 'active' : 'normal'}
          />
          <Text style={{ fontSize: '12px' }}>{progress}% complete</Text>
        </Space>
      )
    },
    {
      title: 'Due Date',
      dataIndex: 'dueDate',
      key: 'dueDate',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (record: any) => (
        <Space>
          <Button
            icon={<EyeOutlined />}

            onClick={() => handleViewRisk(record)}
          >
            View
          </Button>
          <Button
            icon={<EditOutlined />}

            onClick={() => handleEditRisk(record)}
          >
            Edit
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div>
      <Breadcrumb
        items={[
          { title: 'Risk Management', href: '/risk', icon: <SafetyOutlined /> },
          { title: 'Mitigation Plans' }
        ]}
      />

      <div style={{ marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()}>
            Back
          </Button>
        </Space>
      </div>

      <Title level={2}>
        <CheckCircleOutlined style={{ marginRight: 8 }} />
        Risk Mitigation Plans
      </Title>
      <Text type="secondary">
        Track and manage risk treatment actions and mitigation strategies
      </Text>

      {/* Summary Cards */}
      <Row gutter={[16, 16]} style={{ marginTop: 24, marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Space direction="vertical" size={4}>
              <Text type="secondary">Total Plans</Text>
              <Text strong style={{ fontSize: '20px' }}>12</Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Space direction="vertical" size={4}>
              <Text type="secondary">In Progress</Text>
              <Text strong style={{ fontSize: '20px', color: '#2F6FED' }}>8</Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Space direction="vertical" size={4}>
              <Text type="secondary">Overdue</Text>
              <Text strong style={{ fontSize: '20px', color: '#E5484D' }}>2</Text>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card>
        <Table
          columns={columns}
          dataSource={mitigationPlans.map(plan => ({ ...plan, key: plan.id }))}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} plans`
          }}
        />
      </Card>

      {/* View Risk Modal */}
      <Modal
        title={
          <Space>
            <SafetyOutlined />
            <span>{selectedRisk?.riskId}: {selectedRisk?.riskTitle}</span>
          </Space>
        }
        open={isViewModalVisible}
        onCancel={() => setIsViewModalVisible(false)}
        footer={[
          <Button key="edit" type="primary" onClick={() => {
            setIsViewModalVisible(false)
            handleEditRisk(selectedRisk)
          }}>
            Edit Mitigation Plan
          </Button>,
          <Button key="close" onClick={() => setIsViewModalVisible(false)}>
            Close
          </Button>
        ]}
        width={800}
      >
        {selectedRisk && (
          <div>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="Risk Level">
                <PriorityTag status={selectedRisk.riskLevel} />
              </Descriptions.Item>
              <Descriptions.Item label="Category">
                <Tag>{selectedRisk.category}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Impact">
                {selectedRisk.impact}/5
              </Descriptions.Item>
              <Descriptions.Item label="Likelihood">
                {selectedRisk.likelihood}/5
              </Descriptions.Item>
              <Descriptions.Item label="Owner" span={2}>
                <Space>
                  <Text>{selectedRisk.owner}</Text>
                  <Text type="secondary">({selectedRisk.ownerEmail})</Text>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Strategy">
                <Tag color="blue">{selectedRisk.strategy}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Priority">
                <PriorityTag status={selectedRisk.priority} />
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left">Risk Description</Divider>
            <Text>{selectedRisk.description}</Text>

            <Divider orientation="left">Treatment Plan</Divider>
            <Text>{selectedRisk.treatmentPlan}</Text>

            <Divider orientation="left">Current Controls</Divider>
            <Text>{selectedRisk.currentControls}</Text>

            <Divider orientation="left">Mitigation Actions</Divider>
            <Table

              pagination={false}
              dataSource={selectedRisk.actions.map((action: any, index: number) => ({ ...action, key: index }))}
              columns={[
                { title: 'Task', dataIndex: 'task', key: 'task' },
                {
                  title: 'Status',
                  dataIndex: 'status',
                  key: 'status',
                  render: (status: string) => <StatusTag status={status} context="risk" />
                },
                { title: 'Due Date', dataIndex: 'dueDate', key: 'dueDate' }
              ]}
            />

            <Divider orientation="left">Progress</Divider>
            <Progress
              percent={selectedRisk.progress}
              status={selectedRisk.progress === 100 ? 'success' : selectedRisk.progress > 80 ? 'active' : 'normal'}
              strokeWidth={10}
            />
          </div>
        )}
      </Modal>

      {/* Edit Risk Modal */}
      <Modal
        title="Edit Mitigation Plan"
        open={isEditModalVisible}
        onCancel={() => setIsEditModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditSubmit}
        >
          <Form.Item
            name="treatmentPlan"
            label="Treatment Plan"
            rules={[{ required: true, message: 'Please enter treatment plan' }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>

          <Form.Item
            name="currentControls"
            label="Current Controls"
          >
            <Input.TextArea rows={3} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="progress"
                label="Progress (%)"
                rules={[{ required: true, message: 'Please enter progress' }]}
              >
                <Input type="number" min={0} max={100} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="status"
                label="Status"
                rules={[{ required: true, message: 'Please select status' }]}
              >
                <Select>
                  <Select.Option value="pending">Pending</Select.Option>
                  <Select.Option value="in_progress">In Progress</Select.Option>
                  <Select.Option value="completed">Completed</Select.Option>
                  <Select.Option value="on_hold">On Hold</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Update Plan
              </Button>
              <Button onClick={() => setIsEditModalVisible(false)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )

  // Handler functions
  function handleViewRisk(record: any) {
    setSelectedRisk(record)
    setIsViewModalVisible(true)
  }

  function handleEditRisk(record: any) {
    setSelectedRisk(record)
    editForm.setFieldsValue({
      treatmentPlan: record.treatmentPlan,
      currentControls: record.currentControls,
      progress: record.progress,
      status: record.status
    })
    setIsEditModalVisible(true)
  }

  function handleEditSubmit(values: any) {
    try {
      // Simulate API call
      console.log('Updating mitigation plan:', { ...selectedRisk, ...values })
      message.success('Mitigation plan updated successfully!')
      setIsEditModalVisible(false)

      // In a real app, you would refresh the data here
    } catch (error) {
      message.error('Failed to update mitigation plan')
      console.error('Error updating plan:', error)
    }
  }
}