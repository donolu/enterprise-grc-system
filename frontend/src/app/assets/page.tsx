'use client'

import React, { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import { DatabaseOutlined, FileSearchOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import {
  Asset,
  AssetImportResponse,
  createAsset,
  getAssets,
  importAssetRegister,
  updateAsset,
} from '@/lib/services/assetService'

const { Title, Text } = Typography

const assetTypeOptions = [
  { value: 'server', label: 'Server' },
  { value: 'workstation', label: 'Workstation' },
  { value: 'monitor', label: 'Monitor' },
  { value: 'mobile_device', label: 'Mobile device' },
  { value: 'printer', label: 'Printer' },
  { value: 'infrastructure', label: 'Infrastructure' },
  { value: 'application', label: 'Application' },
  { value: 'database', label: 'Database' },
  { value: 'document', label: 'Document' },
  { value: 'other', label: 'Other' },
]

const criticalityOptions = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
]

const classificationOptions = [
  { value: 'public', label: 'Public' },
  { value: 'internal', label: 'Internal' },
  { value: 'confidential', label: 'Confidential' },
  { value: 'restricted', label: 'Restricted' },
]

const lifecycleOptions = [
  { value: 'planned', label: 'Planned' },
  { value: 'active', label: 'Active' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'retired', label: 'Retired' },
  { value: 'disposed', label: 'Disposed' },
]

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null)
  const [form] = Form.useForm()
  const [file, setFile] = useState<File | null>(null)
  const [importSummary, setImportSummary] = useState<AssetImportResponse | null>(null)
  const [importing, setImporting] = useState(false)

  const loadAssets = async (requestedPage = page) => {
    setLoading(true)
    try {
      const data = await getAssets({ search: search || undefined, page: requestedPage })
      setAssets(data.results)
      setTotal(data.count)
      setPage(requestedPage)
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Failed to load assets')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAssets()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const openCreateModal = () => {
    setEditingAsset(null)
    form.resetFields()
    form.setFieldsValue({
      asset_type: 'other',
      classification: 'internal',
      criticality: 'medium',
      lifecycle_status: 'active',
    })
    setModalOpen(true)
  }

  const openEditModal = (asset: Asset) => {
    setEditingAsset(asset)
    form.setFieldsValue(asset)
    setModalOpen(true)
  }

  const saveAsset = async () => {
    const values = await form.validateFields()
    if (editingAsset) {
      await updateAsset(editingAsset.id, values)
      message.success('Asset updated')
    } else {
      await createAsset(values)
      message.success('Asset created')
    }
    setModalOpen(false)
    await loadAssets(page)
  }

  const uploadProps: UploadProps = {
    accept: '.xlsx',
    maxCount: 1,
    beforeUpload: selectedFile => {
      setFile(selectedFile as File)
      setImportSummary(null)
      return false
    },
    onRemove: () => {
      setFile(null)
      setImportSummary(null)
    },
  }

  const runImport = async (dryRun: boolean) => {
    if (!file) {
      message.error('Select an asset register spreadsheet first')
      return
    }
    setImporting(true)
    try {
      const response = await importAssetRegister({ file, dryRun })
      setImportSummary(response)
      message.success(dryRun ? 'Import preview generated' : 'Asset register imported')
      if (!dryRun) await loadAssets(1)
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <DatabaseOutlined style={{ marginRight: 8 }} />
          Asset Register
        </Title>
        <Text type="secondary">
          Track information assets, ownership, classification, risk links and review dates.
        </Text>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="Assets" value={total} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="Overdue reviews" value={assets.filter(asset => asset.is_review_overdue).length} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="Critical assets" value={assets.filter(asset => asset.criticality === 'critical').length} />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} lg={10}>
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="Search assets"
                value={search}
                onChange={event => setSearch(event.target.value)}
                onPressEnter={() => loadAssets(1)}
              />
              <Button onClick={() => loadAssets(1)}>Search</Button>
            </Space.Compact>
          </Col>
          <Col xs={24} lg={14}>
            <Space wrap style={{ justifyContent: 'flex-end', width: '100%' }}>
              <Upload {...uploadProps}>
                <Button icon={<UploadOutlined />}>Select spreadsheet</Button>
              </Upload>
              <Button icon={<FileSearchOutlined />} disabled={!file} loading={importing} onClick={() => runImport(true)}>
                Preview import
              </Button>
              <Button type="primary" icon={<UploadOutlined />} disabled={!file || !importSummary} loading={importing} onClick={() => runImport(false)}>
                Import
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
                New asset
              </Button>
            </Space>
          </Col>
        </Row>

        {importSummary ? (
          <Alert
            style={{ marginTop: 16 }}
            type={importSummary.dry_run ? 'info' : 'success'}
            showIcon
            message={importSummary.dry_run ? 'Import preview ready' : 'Import complete'}
            description={`Importable: ${importSummary.importable_count ?? 0}. Imported: ${importSummary.imported_count ?? 0}. Updated: ${importSummary.updated_count ?? 0}. Skipped rows: ${importSummary.skipped_count}.`}
          />
        ) : null}
      </Card>

      <Card>
        <Table<Asset>
          rowKey="id"
          loading={loading}
          dataSource={assets}
          pagination={{ total, pageSize: 20, current: page }}
          onChange={pagination => loadAssets(pagination.current || 1)}
          onRow={record => ({ onDoubleClick: () => openEditModal(record) })}
          columns={[
            { title: 'Asset ID', dataIndex: 'asset_id', width: 140 },
            { title: 'Name', dataIndex: 'name' },
            { title: 'Type', dataIndex: 'asset_type', width: 140 },
            {
              title: 'Criticality',
              dataIndex: 'criticality',
              width: 120,
              render: value => <Tag color={value === 'critical' ? 'red' : value === 'high' ? 'orange' : 'blue'}>{value}</Tag>,
            },
            { title: 'Owner', dataIndex: 'owner_display', width: 180 },
            { title: 'Location', dataIndex: 'location', width: 180 },
            {
              title: 'Review',
              dataIndex: 'next_review_date',
              width: 140,
              render: (_, asset) => asset.next_review_date ? (
                <Tag color={asset.is_review_overdue ? 'red' : 'default'}>{asset.next_review_date}</Tag>
              ) : null,
            },
            {
              title: '',
              width: 90,
              render: (_, asset) => <Button size="small" onClick={() => openEditModal(asset)}>Edit</Button>,
            },
          ]}
        />
      </Card>

      <Modal
        open={modalOpen}
        title={editingAsset ? 'Edit asset' : 'New asset'}
        onCancel={() => setModalOpen(false)}
        onOk={saveAsset}
        okText={editingAsset ? 'Save' : 'Create'}
        width={760}
      >
        <Form form={form} layout="vertical">
          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item label="Asset ID" name="asset_id" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Name" name="name" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item label="Asset type" name="asset_type">
                <Select options={assetTypeOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Lifecycle" name="lifecycle_status">
                <Select options={lifecycleOptions} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item label="Classification" name="classification">
                <Select options={classificationOptions} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Criticality" name="criticality">
                <Select options={criticalityOptions} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item label="Owner name" name="owner_name">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Location" name="location">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item label="Next review date" name="next_review_date">
                <Input placeholder="YYYY-MM-DD" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item label="Serial number" name="serial_number">
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="Description" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
