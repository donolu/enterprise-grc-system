'use client'

import React, { useState, useEffect } from 'react'
import { Card, Typography, Space, Button, Row, Col, Descriptions, Tag, Progress, Divider, message, Modal, Form, Input, Select, Avatar } from 'antd'
import { TeamOutlined, EditOutlined, DeleteOutlined, ArrowLeftOutlined, GlobalOutlined, MailOutlined, PhoneOutlined } from '@ant-design/icons'
import { useRouter, useParams } from 'next/navigation'
import { Breadcrumb, StatusTag, PriorityTag, Loading } from '@/components/ui'
import { vendorService, type Vendor } from '@/lib/services/vendorService'

const { Title, Text, Paragraph } = Typography

export default function VendorDetailPage() {
  const [loading, setLoading] = useState(true)
  const [vendor, setVendor] = useState<Vendor | null>(null)
  const [isEditModalVisible, setIsEditModalVisible] = useState(false)
  const [editForm] = Form.useForm()
  const router = useRouter()
  const params = useParams()

  // Fetch vendor details
  const fetchVendor = async () => {
    try {
      setLoading(true)
      const data = await vendorService.getVendor(params.id as string)
      setVendor(data)
      editForm.setFieldsValue(data) // Pre-populate edit form
    } catch (error) {
      message.error('Failed to load vendor details')
      console.error('Error fetching vendor:', error)
      // Redirect back to vendor list if vendor not found
      setTimeout(() => router.push('/vendors'), 2000)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchVendor()
  }, [params.id])

  // Handle edit vendor
  const handleEditVendor = () => {
    setIsEditModalVisible(true)
  }

  // Handle edit form submission
  const handleEditSubmit = async (values: any) => {
    try {
      const updatedVendor = await vendorService.updateVendor(params.id as string, values)
      setVendor(updatedVendor)
      message.success('Vendor updated successfully')
      setIsEditModalVisible(false)
    } catch (error) {
      message.error('Failed to update vendor')
      console.error('Error updating vendor:', error)
    }
  }

  // Handle delete vendor
  const handleDeleteVendor = () => {
    Modal.confirm({
      title: 'Are you sure you want to delete this vendor?',
      content: 'This action cannot be undone and will affect all related contracts and assessments.',
      okText: 'Yes, Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await vendorService.deleteVendor(params.id as string)
          message.success('Vendor deleted successfully')
          router.push('/vendors')
        } catch (error) {
          message.error('Failed to delete vendor')
          console.error('Error deleting vendor:', error)
        }
      }
    })
  }

  if (loading) {
    return <Loading message="Loading vendor details..." />
  }

  if (!vendor) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Title level={3}>Vendor Not Found</Title>
        <Text type="secondary">The vendor you're looking for doesn't exist or has been deleted.</Text>
        <br />
        <Button type="primary" onClick={() => router.push('/vendors')} style={{ marginTop: 16 }}>
          Back to Vendor Management
        </Button>
      </div>
    )
  }

  const typeLabels: { [key: string]: string } = {
    'supplier': 'Supplier',
    'service_provider': 'Service Provider',
    'consultant': 'Consultant',
    'contractor': 'Contractor',
    'partner': 'Strategic Partner',
    'subcontractor': 'Subcontractor'
  }

  return (
    <div>
      <Breadcrumb
        items={[
          { title: 'Vendor Management', href: '/vendors', icon: <TeamOutlined /> },
          { title: vendor.name }
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
        {/* Main Vendor Information */}
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <Avatar size="large" style={{ backgroundColor: '#2F6FED' }}>
                  {vendor.name.substring(0, 2).toUpperCase()}
                </Avatar>
                <div>
                  <Text strong style={{ fontSize: '18px' }}>{vendor.name}</Text>
                  <br />
                  <Text type="secondary">{vendor.vendor_id}</Text>
                  {vendor.legal_name && vendor.legal_name !== vendor.name && (
                    <><br /><Text type="secondary" style={{ fontSize: '12px' }}>Legal: {vendor.legal_name}</Text></>
                  )}
                </div>
              </Space>
            }
            extra={
              <Space>
                <Button icon={<EditOutlined />} onClick={handleEditVendor}>
                  Edit
                </Button>
                <Button
                  icon={<DeleteOutlined />}
                  danger
                  onClick={handleDeleteVendor}
                >
                  Delete
                </Button>
              </Space>
            }
          >
            <Descriptions column={2} size="middle">
              <Descriptions.Item label="Status">
                <StatusTag status={vendor.status} context="vendor" />
              </Descriptions.Item>
              <Descriptions.Item label="Vendor Type">
                <Tag>{typeLabels[vendor.vendor_type] || vendor.vendor_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Risk Level">
                <PriorityTag status={vendor.risk_level} />
              </Descriptions.Item>
              <Descriptions.Item label="Risk Score">
                {vendor.risk_score ? (
                  <Space>
                    <Text strong>{vendor.risk_score}</Text>
                    <Progress
                      percent={Math.min((vendor.risk_score / 100) * 100, 100)}

                      style={{ width: 100 }}
                      status={vendor.risk_score >= 70 ? 'exception' : vendor.risk_score >= 40 ? 'active' : 'success'}
                    />
                  </Space>
                ) : (
                  <Text type="secondary">Not assessed</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Category">
                {vendor.category ? (
                  <Tag color={vendor.category.color_code || 'default'}>{vendor.category.name}</Tag>
                ) : (
                  <Text type="secondary">Uncategorized</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Annual Spend">
                {vendor.annual_spend ?
                  <Text strong>${vendor.annual_spend.toLocaleString()}</Text> :
                  <Text type="secondary">Not specified</Text>
                }
              </Descriptions.Item>
              <Descriptions.Item label="Owner">
                {vendor.assigned_to ? (
                  <Text>{vendor.assigned_to.first_name} {vendor.assigned_to.last_name}</Text>
                ) : (
                  <Text type="secondary">Unassigned</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Payment Terms">
                {vendor.payment_terms || <Text type="secondary">Not specified</Text>}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <div>
              <Title level={5}>Business Information</Title>

              {vendor.website && (
                <div style={{ marginBottom: 12 }}>
                  <Space>
                    <GlobalOutlined />
                    <a href={vendor.website} target="_blank" rel="noopener noreferrer">
                      {vendor.website}
                    </a>
                  </Space>
                </div>
              )}

              {vendor.business_description && (
                <Paragraph>
                  {vendor.business_description}
                </Paragraph>
              )}

              {(vendor.address_line1 || vendor.city || vendor.country) && (
                <>
                  <Title level={5}>Address</Title>
                  <Paragraph>
                    {vendor.address_line1 && <>{vendor.address_line1}<br /></>}
                    {vendor.address_line2 && <>{vendor.address_line2}<br /></>}
                    {vendor.city && vendor.state_province && vendor.postal_code && (
                      <>{vendor.city}, {vendor.state_province} {vendor.postal_code}<br /></>
                    )}
                    {vendor.country && <>{vendor.country}</>}
                  </Paragraph>
                </>
              )}

              {vendor.certifications && vendor.certifications.length > 0 && (
                <>
                  <Title level={5}>Certifications</Title>
                  <Space wrap>
                    {vendor.certifications.map((cert, index) => (
                      <Tag key={index} color="green">{cert}</Tag>
                    ))}
                  </Space>
                </>
              )}

              {vendor.operating_regions && vendor.operating_regions.length > 0 && (
                <>
                  <Title level={5} style={{ marginTop: 16 }}>Operating Regions</Title>
                  <Space wrap>
                    {vendor.operating_regions.map((region, index) => (
                      <Tag key={index} color="blue">{region}</Tag>
                    ))}
                  </Space>
                </>
              )}
            </div>
          </Card>
        </Col>

        {/* Vendor Metadata and Compliance */}
        <Col xs={24} lg={8}>
          <Card title="Compliance & Security" style={{ marginBottom: 16 }}>
            <Descriptions column={1}>
              <Descriptions.Item label="DPA in Place">
                <Tag color={vendor.data_processing_agreement ? 'green' : 'red'}>
                  {vendor.data_processing_agreement ? 'Yes' : 'No'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Security Assessment">
                <Tag color={vendor.security_assessment_completed ? 'green' : 'orange'}>
                  {vendor.security_assessment_completed ? 'Completed' : 'Pending'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Assessment Date">
                {vendor.security_assessment_date ?
                  new Date(vendor.security_assessment_date).toLocaleDateString() :
                  <Text type="secondary">Not completed</Text>
                }
              </Descriptions.Item>
              <Descriptions.Item label="Tax ID">
                {vendor.tax_id || <Text type="secondary">Not provided</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="DUNS Number">
                {vendor.duns_number || <Text type="secondary">Not provided</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="Credit Rating">
                {vendor.credit_rating || <Text type="secondary">Not rated</Text>}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="Vendor Activity">
            <Descriptions column={1}>
              <Descriptions.Item label="Relationship Start">
                {vendor.relationship_start_date ?
                  new Date(vendor.relationship_start_date).toLocaleDateString() :
                  <Text type="secondary">Not specified</Text>
                }
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {new Date(vendor.created_at).toLocaleDateString()}
              </Descriptions.Item>
              <Descriptions.Item label="Created By">
                {vendor.created_by ?
                  `${vendor.created_by.first_name} ${vendor.created_by.last_name}` :
                  <Text type="secondary">System</Text>
                }
              </Descriptions.Item>
              <Descriptions.Item label="Last Updated">
                {new Date(vendor.updated_at).toLocaleDateString()}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {/* Edit Vendor Modal */}
      <Modal
        title="Edit Vendor"
        open={isEditModalVisible}
        onCancel={() => setIsEditModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Vendor Name"
                rules={[{ required: true, message: 'Please enter vendor name' }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="legal_name"
                label="Legal Name"
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="business_description"
            label="Business Description"
          >
            <Input.TextArea rows={3} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="website"
                label="Website"
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="annual_spend"
                label="Annual Spend"
              >
                <Input type="number" addonBefore="$" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Update Vendor
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