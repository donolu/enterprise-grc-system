'use client'

import React, { useState, useEffect } from 'react'
import { Input, AutoComplete, Space, Tag, Typography } from 'antd'
import { SearchOutlined, FileTextOutlined, TeamOutlined, SafetyOutlined, CheckSquareOutlined, VideoCameraOutlined } from '@ant-design/icons'
import { useTheme } from '@/theme'

const { Text } = Typography

interface SearchOption {
  value: string
  label: React.ReactNode
  category: string
  href: string
}

interface SearchBarProps {
  placeholder?: string
  onSelect?: (value: string, option: SearchOption) => void
  style?: React.CSSProperties
  size?: 'small' | 'middle' | 'large'
}

export const SearchBar: React.FC<SearchBarProps> = ({
  placeholder = "Search controls, vendors, risks, policies...",
  onSelect,
  style,
  size = 'large'
}) => {
  const { mode } = useTheme()
  const isDark = mode === 'dark'
  const [searchValue, setSearchValue] = useState('')
  const [options, setOptions] = useState<SearchOption[]>([])

  // Mock search data - replace with real API calls
  const mockSearchData: SearchOption[] = [
    // Policies
    { value: 'Information Security Policy', label: 'Information Security Policy', category: 'Policies', href: '/policies' },
    { value: 'Data Privacy Policy', label: 'Data Privacy Policy', category: 'Policies', href: '/policies' },
    { value: 'Access Control Policy', label: 'Access Control Policy', category: 'Policies', href: '/policies' },

    // Vendors
    { value: 'Microsoft Corporation', label: 'Microsoft Corporation', category: 'Vendors', href: '/vendors' },
    { value: 'Amazon Web Services', label: 'Amazon Web Services', category: 'Vendors', href: '/vendors' },
    { value: 'Salesforce Inc', label: 'Salesforce Inc', category: 'Vendors', href: '/vendors' },

    // Risks
    { value: 'Data Breach Risk', label: 'Data Breach Risk', category: 'Risks', href: '/risk' },
    { value: 'Third Party Risk', label: 'Third Party Risk', category: 'Risks', href: '/risk' },
    { value: 'Compliance Risk', label: 'Compliance Risk', category: 'Risks', href: '/risk' },

    // Controls/Assessments
    { value: 'Access Management', label: 'Access Management', category: 'Controls', href: '/assessments' },
    { value: 'Incident Response', label: 'Incident Response', category: 'Controls', href: '/assessments' },
    { value: 'Data Classification', label: 'Data Classification', category: 'Controls', href: '/assessments' },

    // Training
    { value: 'Phishing Awareness', label: 'Phishing Awareness', category: 'Training', href: '/training' },
    { value: 'Security Fundamentals', label: 'Security Fundamentals', category: 'Training', href: '/training' },
  ]

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Policies': return <FileTextOutlined />
      case 'Vendors': return <TeamOutlined />
      case 'Risks': return <SafetyOutlined />
      case 'Controls': return <CheckSquareOutlined />
      case 'Training': return <VideoCameraOutlined />
      default: return <SearchOutlined />
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'Policies': return '#FFB020'
      case 'Vendors': return '#3B82F6'
      case 'Risks': return '#E5484D'
      case 'Controls': return '#0EB57D'
      case 'Training': return '#722ED1'
      default: return '#2F6FED'
    }
  }

  const handleSearch = (value: string) => {
    setSearchValue(value)

    if (!value.trim()) {
      setOptions([])
      return
    }

    // Filter options based on search value
    const filteredOptions = mockSearchData
      .filter(item =>
        item.value.toLowerCase().includes(value.toLowerCase())
      )
      .slice(0, 10) // Limit to 10 results
      .map(item => ({
        ...item,
        label: (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '4px 0'
          }}>
            <Space>
              {getCategoryIcon(item.category)}
              <Text style={{ color: isDark ? '#F8FAFC' : '#0F172A' }}>
                {item.value}
              </Text>
            </Space>
            <Tag
              color={getCategoryColor(item.category)}
              style={{
                fontSize: '11px',
                margin: 0,
                borderRadius: 4
              }}
            >
              {item.category}
            </Tag>
          </div>
        )
      }))

    setOptions(filteredOptions)
  }

  const handleSelect = (value: string, option: any) => {
    const selectedOption = mockSearchData.find(item => item.value === value)
    if (selectedOption) {
      // Navigate to the selected item's page
      window.location.href = selectedOption.href
      if (onSelect) {
        onSelect(value, selectedOption)
      }
    }
    setSearchValue('')
    setOptions([])
  }

  return (
    <AutoComplete
      value={searchValue}
      options={options}
      onSearch={handleSearch}
      onSelect={handleSelect}
      style={{
        width: '100%',
        maxWidth: 440,
        ...style
      }}
    >
      <Input.Search
        placeholder={placeholder}
        size={size}
        style={{
          borderRadius: 8,
        }}
        suffix={
          <SearchOutlined style={{
            color: isDark ? '#64748B' : '#94A3B8',
            fontSize: 16
          }} />
        }
      />
    </AutoComplete>
  )
}

export default SearchBar