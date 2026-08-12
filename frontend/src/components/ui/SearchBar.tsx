'use client'

import React, { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AutoComplete, Input, Space, Tag, Typography } from 'antd'
import {
  SafetyOutlined,
  SearchOutlined,
  TeamOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import { api, getErrorMessage } from '@/lib/api'
import { useTheme } from '@/theme'

const { Text } = Typography

type SearchEntityType = 'risk' | 'vendor' | 'training'

interface SearchResult {
  id: string
  entity_type: SearchEntityType
  title: string
  context: string
  href: string
}

interface SearchResponse {
  query: string
  results: SearchResult[]
}

interface SearchOption {
  value: string
  label: React.ReactNode
  result: SearchResult
}

interface SearchBarProps {
  placeholder?: string
  onSelect?: (value: string, option: SearchOption) => void
  style?: React.CSSProperties
  size?: 'small' | 'middle' | 'large'
}

const labels: Record<SearchEntityType, string> = {
  risk: 'Risk',
  vendor: 'Vendor',
  training: 'Training',
}

const icons: Record<SearchEntityType, React.ReactNode> = {
  risk: <SafetyOutlined />,
  vendor: <TeamOutlined />,
  training: <VideoCameraOutlined />,
}

const colours: Record<SearchEntityType, string> = {
  risk: '#E5484D',
  vendor: '#2F6FED',
  training: '#0F766E',
}

export const SearchBar: React.FC<SearchBarProps> = ({
  placeholder = 'Search risks, vendors and training...',
  onSelect,
  style,
  size = 'large',
}) => {
  const router = useRouter()
  const { mode } = useTheme()
  const isDark = mode === 'dark'
  const [searchValue, setSearchValue] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const query = searchValue.trim()
    if (query.length < 2) {
      setResults([])
      setError(null)
      setLoading(false)
      return
    }

    const controller = new AbortController()
    const timeout = window.setTimeout(async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await api.get<SearchResponse>('/search/', {
          params: { q: query },
          signal: controller.signal,
        })
        setResults(response.data.results)
      } catch (requestError: unknown) {
        if (!controller.signal.aborted) {
          setResults([])
          setError(getErrorMessage(requestError))
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }, 250)

    return () => {
      controller.abort()
      window.clearTimeout(timeout)
    }
  }, [searchValue])

  const options = useMemo<SearchOption[]>(() => results.map((result) => ({
    value: `${result.entity_type}:${result.id}`,
    result,
    label: (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '4px 0' }}>
        <Space size={8}>
          {icons[result.entity_type]}
          <span>
            <Text style={{ color: isDark ? '#F8FAFC' : '#0F172A' }}>{result.title}</Text>
            {result.context && (
              <Text type="secondary" style={{ display: 'block', fontSize: 12 }}>{result.context}</Text>
            )}
          </span>
        </Space>
        <Tag color={colours[result.entity_type]} style={{ margin: 0 }}>{labels[result.entity_type]}</Tag>
      </div>
    ),
  })), [isDark, results])

  const handleSelect = (value: string) => {
    const option = options.find((candidate) => candidate.value === value)
    if (!option) return

    router.push(option.result.href)
    onSelect?.(value, option)
    setSearchValue('')
    setResults([])
  }

  const query = searchValue.trim()
  const notFoundContent = query.length < 2
    ? 'Enter at least two characters'
    : loading
      ? 'Searching your organisation...'
      : error
        ? `Search is unavailable: ${error}`
        : 'No matching records'

  return (
    <AutoComplete
      value={searchValue}
      options={options}
      onSearch={setSearchValue}
      onSelect={handleSelect}
      notFoundContent={notFoundContent}
      style={{ width: '100%', maxWidth: 440, ...style }}
    >
      <Input
        placeholder={placeholder}
        size={size}
        aria-label="Global search"
        suffix={<SearchOutlined style={{ color: isDark ? '#64748B' : '#94A3B8', fontSize: 16 }} />}
      />
    </AutoComplete>
  )
}

export default SearchBar
