'use client'

import React from 'react'
import { Spin, Space, Typography } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'
import { useTheme } from '@/theme'

const { Text } = Typography

interface LoadingProps {
  message?: string
  size?: 'small' | 'default' | 'large'
  spinning?: boolean
  children?: React.ReactNode
  style?: React.CSSProperties
  centered?: boolean
}

export const Loading: React.FC<LoadingProps> = ({
  message,
  size = 'large',
  spinning = true,
  children,
  style,
  centered = true
}) => {
  const { mode } = useTheme()
  const isDark = mode === 'dark'

  const antIcon = <LoadingOutlined style={{
    fontSize: size === 'small' ? 16 : size === 'large' ? 32 : 24,
    color: '#2F6FED'
  }} spin />

  if (children) {
    return (
      <Spin
        spinning={spinning}
        indicator={antIcon}
        style={style}
      >
        {children}
      </Spin>
    )
  }

  const content = (
    <Space direction="vertical" size={12} align="center">
      <Spin indicator={antIcon} />
      {message && (
        <Text style={{
          color: isDark ? '#94A3B8' : '#64748B',
          fontSize: size === 'small' ? 12 : size === 'large' ? 16 : 14
        }}>
          {message}
        </Text>
      )}
    </Space>
  )

  if (centered) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: 200,
        ...style
      }}>
        {content}
      </div>
    )
  }

  return <div style={style}>{content}</div>
}

export default Loading