'use client'

import React, { useState } from 'react'
import { Card, Space, Select, DatePicker, Input, Button, Row, Col, Collapse, Badge } from 'antd'
import { FilterOutlined, ClearOutlined, SearchOutlined } from '@ant-design/icons'
import { useTheme } from '@/theme'

const { Option } = Select
const { RangePicker } = DatePicker

interface FilterOption {
  key: string
  label: string
  type: 'select' | 'multiSelect' | 'search' | 'dateRange' | 'text'
  options?: { value: string; label: string }[]
  placeholder?: string
}

interface FilterPanelProps {
  filters: FilterOption[]
  onFilterChange?: (filters: Record<string, any>) => void
  onClear?: () => void
  defaultOpen?: boolean
  showCount?: boolean
  className?: string
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onFilterChange,
  onClear,
  defaultOpen = false,
  showCount = true,
  className
}) => {
  const { mode } = useTheme()
  const isDark = mode === 'dark'
  const [filterValues, setFilterValues] = useState<Record<string, any>>({})
  const [isOpen, setIsOpen] = useState(defaultOpen)

  const handleFilterChange = (key: string, value: any) => {
    const newFilters = { ...filterValues, [key]: value }

    // Remove empty values
    if (value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0)) {
      delete newFilters[key]
    }

    setFilterValues(newFilters)
    onFilterChange?.(newFilters)
  }

  const handleClearAll = () => {
    setFilterValues({})
    onFilterChange?.({})
    onClear?.()
  }

  const activeFilterCount = Object.keys(filterValues).length

  const renderFilter = (filter: FilterOption) => {
    switch (filter.type) {
      case 'select':
        return (
          <Select
            placeholder={filter.placeholder || `Select ${filter.label}`}
            style={{ width: '100%' }}
            allowClear
            value={filterValues[filter.key]}
            onChange={(value) => handleFilterChange(filter.key, value)}
          >
            {filter.options?.map(option => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        )

      case 'multiSelect':
        return (
          <Select
            mode="multiple"
            placeholder={filter.placeholder || `Select ${filter.label}`}
            style={{ width: '100%' }}
            allowClear
            value={filterValues[filter.key]}
            onChange={(value) => handleFilterChange(filter.key, value)}
          >
            {filter.options?.map(option => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        )

      case 'search':
        return (
          <Input.Search
            placeholder={filter.placeholder || `Search ${filter.label}`}
            allowClear
            value={filterValues[filter.key]}
            onChange={(e) => handleFilterChange(filter.key, e.target.value)}
            onSearch={(value) => handleFilterChange(filter.key, value)}
          />
        )

      case 'text':
        return (
          <Input
            placeholder={filter.placeholder || filter.label}
            allowClear
            value={filterValues[filter.key]}
            onChange={(e) => handleFilterChange(filter.key, e.target.value)}
          />
        )

      case 'dateRange':
        return (
          <RangePicker
            style={{ width: '100%' }}
            placeholder={['Start Date', 'End Date']}
            value={filterValues[filter.key]}
            onChange={(dates) => handleFilterChange(filter.key, dates)}
          />
        )

      default:
        return null
    }
  }

  const panelHeader = (
    <Space>
      <FilterOutlined style={{ color: '#2F6FED' }} />
      <span>Advanced Filters</span>
      {showCount && activeFilterCount > 0 && (
        <Badge
          count={activeFilterCount}
          style={{ backgroundColor: '#2F6FED' }}
        />
      )}
    </Space>
  )

  const collapseItems = [{
    key: 'filters',
    label: panelHeader,
    children: (
      <>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {filters.map((filter, index) => (
            <Col
              key={filter.key}
              xs={24}
              sm={12}
              md={8}
              lg={6}
              xl={filters.length <= 4 ? 24/filters.length : 6}
            >
              <div>
                <label
                  style={{
                    display: 'block',
                    marginBottom: 4,
                    fontSize: '12px',
                    fontWeight: 500,
                    color: isDark ? '#CBD5E1' : '#64748B'
                  }}
                >
                  {filter.label}
                </label>
                {renderFilter(filter)}
              </div>
            </Col>
          ))}
        </Row>

        {activeFilterCount > 0 && (
          <Row justify="end" style={{ marginTop: 16 }}>
            <Space>
              <Button
                icon={<ClearOutlined />}
                onClick={handleClearAll}

              >
                Clear All Filters
              </Button>
            </Space>
          </Row>
        )}
      </>
    )
  }]

  return (
    <Card className={className} style={{ marginBottom: 16 }}>
      <Collapse
        ghost
        activeKey={isOpen ? ['filters'] : []}
        onChange={(key) => setIsOpen(key.includes('filters'))}
        items={collapseItems}
      />
    </Card>
  )
}

// Preset filter configurations for common use cases
export const RiskFilters: FilterOption[] = [
  {
    key: 'riskLevel',
    label: 'Risk Level',
    type: 'multiSelect',
    options: [
      { value: 'low', label: 'Low' },
      { value: 'medium', label: 'Medium' },
      { value: 'high', label: 'High' },
      { value: 'critical', label: 'Critical' }
    ]
  },
  {
    key: 'status',
    label: 'Status',
    type: 'multiSelect',
    options: [
      { value: 'open', label: 'Open' },
      { value: 'in_progress', label: 'In Progress' },
      { value: 'under_review', label: 'Under Review' },
      { value: 'closed', label: 'Closed' }
    ]
  },
  {
    key: 'category',
    label: 'Category',
    type: 'multiSelect',
    options: [
      { value: 'cybersecurity', label: 'Cybersecurity' },
      { value: 'compliance', label: 'Compliance' },
      { value: 'operational', label: 'Operational' },
      { value: 'financial', label: 'Financial' }
    ]
  },
  {
    key: 'owner',
    label: 'Risk Owner',
    type: 'search',
    placeholder: 'Search by owner name'
  },
  {
    key: 'dateRange',
    label: 'Date Range',
    type: 'dateRange'
  }
]

export const VendorFilters: FilterOption[] = [
  {
    key: 'riskLevel',
    label: 'Risk Level',
    type: 'select',
    options: [
      { value: 'low', label: 'Low' },
      { value: 'medium', label: 'Medium' },
      { value: 'high', label: 'High' },
      { value: 'critical', label: 'Critical' }
    ]
  },
  {
    key: 'status',
    label: 'Status',
    type: 'multiSelect',
    options: [
      { value: 'active', label: 'Active' },
      { value: 'under_review', label: 'Under Review' },
      { value: 'inactive', label: 'Inactive' },
      { value: 'pending', label: 'Pending' }
    ]
  },
  {
    key: 'category',
    label: 'Category',
    type: 'multiSelect',
    options: [
      { value: 'cloud_services', label: 'Cloud Services' },
      { value: 'infrastructure', label: 'Infrastructure' },
      { value: 'software', label: 'Software' },
      { value: 'security', label: 'Security' }
    ]
  },
  {
    key: 'spend',
    label: 'Annual Spend',
    type: 'select',
    options: [
      { value: 'under_50k', label: 'Under $50K' },
      { value: '50k_100k', label: '$50K - $100K' },
      { value: '100k_500k', label: '$100K - $500K' },
      { value: 'over_500k', label: 'Over $500K' }
    ]
  },
  {
    key: 'contractExpiry',
    label: 'Contract Expiry',
    type: 'select',
    options: [
      { value: 'expired', label: 'Expired' },
      { value: 'expiring_30', label: 'Expiring in 30 days' },
      { value: 'expiring_90', label: 'Expiring in 90 days' },
      { value: 'expiring_180', label: 'Expiring in 6 months' }
    ]
  }
]

export default FilterPanel