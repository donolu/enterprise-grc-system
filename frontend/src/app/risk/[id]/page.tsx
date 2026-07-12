'use client'

import React, { useState, useEffect } from 'react'
import { Card, Typography, Space, Button, Row, Col, Descriptions, Tag, Progress, Divider, message, Modal, Form, Input, Select } from 'antd'
import { SafetyOutlined, EditOutlined, DeleteOutlined, ArrowLeftOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { useRouter, useParams } from 'next/navigation'
import { Breadcrumb, StatusTag, PriorityTag, Loading } from '@/components/ui'
import { riskService, type Risk } from '@/lib/services/riskService'

const { Title, Text, Paragraph } = Typography

export default function RiskDetailPage() {
  const [loading, setLoading] = useState(true)
  const [risk, setRisk] = useState<Risk | null>(null)
  const [isEditModalVisible, setIsEditModalVisible] = useState(false)
  const [editForm] = Form.useForm()
  const router = useRouter()
  const params = useParams()

  // Fetch risk details
  const fetchRisk = async () => {
    try {
      setLoading(true)
      const data = await riskService.getRisk(params.id as string)
      setRisk(data)
      editForm.setFieldsValue(data) // Pre-populate edit form
    } catch (error) {
      message.error('Failed to load risk details')
      console.error('Error fetching risk:', error)
      // Redirect back to risk list if risk not found
      setTimeout(() => router.push('/risk'), 2000)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRisk()
  }, [params.id])

  // Handle edit risk
  const handleEditRisk = () => {
    setIsEditModalVisible(true)
  }

  // Handle edit form submission
  const handleEditSubmit = async (values: any) => {
    try {
      const updatedRisk = await riskService.updateRisk(params.id as string, values)
      setRisk(updatedRisk)
      message.success('Risk updated successfully')
      setIsEditModalVisible(false)
    } catch (error) {
      message.error('Failed to update risk')
      console.error('Error updating risk:', error)
    }
  }

  // Handle delete risk
  const handleDeleteRisk = () => {
    Modal.confirm({
      title: 'Are you sure you want to delete this risk?',
      content: 'This action cannot be undone.',
      okText: 'Yes, Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await riskService.deleteRisk(params.id as string)
          message.success('Risk deleted successfully')
          router.push('/risk')
        } catch (error) {
          message.error('Failed to delete risk')
          console.error('Error deleting risk:', error)
        }
      }
    })
  }

  if (loading) {
    return <Loading message="Loading risk details..." />
  }

  if (!risk) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Title level={3}>Risk Not Found</Title>
        <Text type="secondary">The risk you&apos;re looking for doesn&apos;t exist or has been deleted.</Text>
        <br />
        <Button type="primary" onClick={() => router.push('/risk')} style={{ marginTop: 16 }}>
          Back to Risk Management
        </Button>
      </div>
    )
  }

  return (
    <div>
      <Breadcrumb
        items={[
          { title: 'Risk Management', href: '/risk', icon: <SafetyOutlined /> },
          { title: risk.risk_id }
        ]}
      />

      <div style={{ marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()}>
            Back
          </Button>
        </Space>
      </div>

      <Row gutter={[24, 24]}>
        {/* Main Risk Information */}
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <SafetyOutlined />
                <Text strong>{risk.title}</Text>
              </Space>
            }
            extra={
              <Space>
                <Button icon={<EditOutlined />} onClick={handleEditRisk}>
                  Edit
                </Button>
                <Button
                  icon={<DeleteOutlined />}
                  danger
                  onClick={handleDeleteRisk}
                >
                  Delete
                </Button>
              </Space>
            }
          >
            <Descriptions column={2} size="middle">
              <Descriptions.Item label="Risk ID">
                <Text strong style={{ color: '#2F6FED' }}>{risk.risk_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <StatusTag status={risk.status} context="risk" />
              </Descriptions.Item>
              <Descriptions.Item label="Risk Level">
                <PriorityTag status={risk.risk_level} />
              </Descriptions.Item>
              <Descriptions.Item label="Risk Score">
                <Space>
                  <Text strong>{risk.risk_score}</Text>
                  <Progress
                    percent={(risk.risk_score / 25) * 100}

                    style={{ width: 100 }}
                    status={risk.risk_score > 15 ? 'exception' : risk.risk_score > 10 ? 'active' : 'success'}
                  />
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Category">
                {risk.category ? (
                  <Tag color={risk.category.color || 'default'}>{risk.category.name}</Tag>
                ) : (
                  <Text type="secondary">Uncategorized</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Owner">
                {risk.risk_owner ? (
                  <Text>{risk.risk_owner.first_name} {risk.risk_owner.last_name}</Text>
                ) : (
                  <Text type="secondary">Unassigned</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Impact Level">
                <Text>{risk.impact}/5</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Likelihood">
                <Text>{risk.likelihood}/5</Text>
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <div>
              <Title level={5}>Description</Title>
              <Paragraph>
                {risk.description || <Text type="secondary">No description provided</Text>}
              </Paragraph>

              {risk.potential_impact_description && (
                <>
                  <Title level={5}>Potential Impact</Title>
                  <Paragraph>
                    {risk.potential_impact_description}
                  </Paragraph>
                </>
              )}

              {risk.current_controls && (
                <>
                  <Title level={5}>Current Controls</Title>
                  <Paragraph>
                    {risk.current_controls}
                  </Paragraph>
                </>
              )}

              {risk.treatment_description && (
                <>
                  <Title level={5}>Treatment Plan</Title>
                  <Paragraph>
                    <Tag color="blue" style={{ marginBottom: 8 }}>
                      Strategy: {risk.treatment_strategy?.toUpperCase()}
                    </Tag>
                    <br />
                    {risk.treatment_description}
                  </Paragraph>
                </>
              )}
            </div>
          </Card>
        </Col>

        {/* Risk Timeline and Metadata */}
        <Col xs={24} lg={8}>
          <Card title="Risk Timeline" style={{ marginBottom: 16 }}>
            <Descriptions column={1}>
              <Descriptions.Item label="Identified">
                {new Date(risk.identified_date).toLocaleDateString()}
              </Descriptions.Item>
              <Descriptions.Item label="Last Assessed">
                {risk.last_assessed_date ?
                  new Date(risk.last_assessed_date).toLocaleDateString() :
                  <Text type="secondary">Not assessed</Text>
                }
              </Descriptions.Item>
              <Descriptions.Item label="Next Review">
                {risk.next_review_date ? (
                  <Space direction="vertical" size={2}>
                    <Text>{new Date(risk.next_review_date).toLocaleDateString()}</Text>
                    {risk.is_overdue_for_review && (
                      <Tag color="red" icon={<ExclamationCircleOutlined />}>
                        Overdue
                      </Tag>
                    )}
                  </Space>
                ) : (
                  <Text type="secondary">Not scheduled</Text>
                )}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="Risk Activity">
            <Descriptions column={1}>
              <Descriptions.Item label="Created">
                {new Date(risk.created_at).toLocaleDateString()}
              </Descriptions.Item>
              <Descriptions.Item label="Created By">
                {risk.created_by ?
                  `${risk.created_by.first_name} ${risk.created_by.last_name}` :
                  <Text type="secondary">System</Text>
                }
              </Descriptions.Item>
              <Descriptions.Item label="Last Updated">
                {new Date(risk.updated_at).toLocaleDateString()}
              </Descriptions.Item>
              <Descriptions.Item label="Active">
                <Tag color={risk.is_active ? 'green' : 'red'}>
                  {risk.is_active ? 'Yes' : 'No'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {/* Edit Risk Modal */}
      <Modal
        title="Edit Risk"
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
            name="title"
            label="Risk Title"
            rules={[{ required: true, message: 'Please enter risk title' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <Input.TextArea rows={3} />
          </Form.Item>

          <Form.Item
            name="treatment_description"
            label="Treatment Description"
          >
            <Input.TextArea rows={2} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="impact"
                label="Impact (1-5)"
                rules={[{ required: true, message: 'Please select impact' }]}
              >
                <Select>
                  {[1, 2, 3, 4, 5].map(num => (
                    <Select.Option key={num} value={num}>{num}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="likelihood"
                label="Likelihood (1-5)"
                rules={[{ required: true, message: 'Please select likelihood' }]}
              >
                <Select>
                  {[1, 2, 3, 4, 5].map(num => (
                    <Select.Option key={num} value={num}>{num}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Update Risk
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
}