'use client'

import React from 'react'
import { Breadcrumb as AntBreadcrumb, Typography } from 'antd'
import { HomeOutlined } from '@ant-design/icons'
import Link from 'next/link'
import { useTheme } from '@/theme'

interface BreadcrumbItem {
  title: string
  href?: string
  icon?: React.ReactNode
}

interface BreadcrumbProps {
  items: BreadcrumbItem[]
  showHome?: boolean
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({
  items,
  showHome = true
}) => {
  const { mode } = useTheme()
  const isDark = mode === 'dark'

  const breadcrumbItems = [
    ...(showHome ? [{
      title: (
        <Link href="/" style={{
          color: isDark ? '#94A3B8' : '#64748B',
          textDecoration: 'none'
        }}>
          <HomeOutlined style={{ marginRight: 4 }} />
          Dashboard
        </Link>
      )
    }] : []),
    ...items.map((item, index) => ({
      title: item.href && index < items.length - 1 ? (
        <Link href={item.href} style={{
          color: isDark ? '#94A3B8' : '#64748B',
          textDecoration: 'none'
        }}>
          {item.icon && <span style={{ marginRight: 4 }}>{item.icon}</span>}
          {item.title}
        </Link>
      ) : (
        <span style={{
          color: isDark ? '#F8FAFC' : '#0F172A',
          fontWeight: 500
        }}>
          {item.icon && <span style={{ marginRight: 4 }}>{item.icon}</span>}
          {item.title}
        </span>
      )
    }))
  ]

  return (
    <div style={{ marginBottom: 16 }}>
      <AntBreadcrumb
        items={breadcrumbItems}
        style={{
          fontSize: 14,
          color: isDark ? '#94A3B8' : '#64748B'
        }}
        separator={<span style={{ color: isDark ? '#64748B' : '#94A3B8' }}>{'>'}</span>}
      />
    </div>
  )
}

export default Breadcrumb