'use client'

import React, { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, Row, Col, Typography, Button, Select, Input, Tag } from 'antd'
import { PlayCircleOutlined, SearchOutlined, ClockCircleOutlined, UserOutlined } from '@ant-design/icons'
import { api, getErrorMessage } from '@/lib/api'
import { EmptyState, Loading, PageHeader } from '@/components/ui'

const { Text, Paragraph } = Typography
const { Search } = Input
const { Option } = Select

interface TrainingCategory {
  id: string
  name: string
  description: string
  color: string
  videos_count: number
}

interface TrainingVideo {
  id: string
  title: string
  description: string
  category_name: string
  category_color: string
  video_provider: string
  duration_minutes: number | null
  difficulty_level: string
  view_count: number
  created_by_name: string
  created_at: string
  embed_url?: string
}

export default function TrainingPage() {
  const router = useRouter()
  const [videos, setVideos] = useState<TrainingVideo[]>([])
  const [categories, setCategories] = useState<TrainingCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('')

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setLoadError(null)
      const [videosResponse, categoriesResponse] = await Promise.all([
        api.get<{ results?: TrainingVideo[] } | TrainingVideo[]>('/training/videos/'),
        api.get<{ results?: TrainingCategory[] } | TrainingCategory[]>('/training/categories/')
      ])
      const videoData = videosResponse.data
      const categoryData = categoriesResponse.data
      setVideos(Array.isArray(videoData) ? videoData : videoData.results || [])
      setCategories(Array.isArray(categoryData) ? categoryData : categoryData.results || [])
    } catch (error: unknown) {
      setVideos([])
      setCategories([])
      setLoadError(getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  const handleVideoClick = (video: TrainingVideo) => {
    router.push(`/training/video/${video.id}`)
  }

  const filteredVideos = videos.filter(video => {
    const matchesSearch = !searchTerm ||
      video.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      video.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      video.category_name.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesCategory = !selectedCategory || video.category_name === selectedCategory
    const matchesDifficulty = !selectedDifficulty || video.difficulty_level === selectedDifficulty

    return matchesSearch && matchesCategory && matchesDifficulty
  })

  const getDifficultyColor = (level: string) => {
    switch (level) {
      case 'beginner': return 'green'
      case 'intermediate': return 'orange'
      case 'advanced': return 'red'
      default: return 'default'
    }
  }

  const formatDuration = (minutes: number | null) => {
    if (!minutes) return 'Duration not specified'
    if (minutes < 60) return `${minutes} min`
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return `${hours}h ${remainingMinutes}m`
  }

  if (loading) {
    return <Loading message="Loading training content..." />
  }

  return (
    <div>
      <PageHeader
        eyebrow="SECURITY AWARENESS"
        title="Training library"
        description="Build practical security awareness with focused training for your organisation."
        icon={<PlayCircleOutlined />}
      />

      {loadError ? (
        <EmptyState
          type="error"
          title="Training content could not be loaded"
          description={loadError}
          action={{ text: 'Try again', onClick: () => void fetchData() }}
        />
      ) : (
        <>
      {/* Category Overview */}
      {categories.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          {categories.map(category => (
            <Col xs={24} sm={12} md={6} key={category.id}>
              <Card
                style={{
                  borderLeftColor: category.color,
                  borderLeftWidth: '4px',
                  cursor: 'pointer'
                }}
                onClick={() => setSelectedCategory(selectedCategory === category.name ? '' : category.name)}
                hoverable
              >
                <div style={{ textAlign: 'center' }}>
                  <div style={{ color: category.color, fontSize: '24px', marginBottom: 8 }}>
                    {category.videos_count}
                  </div>
                  <Text strong>{category.name}</Text>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* Filters */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder="Search videos by title, description, or category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              allowClear
              prefix={<SearchOutlined />}
            />
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder="Category"
              value={selectedCategory}
              onChange={setSelectedCategory}
              allowClear
              style={{ width: '100%' }}
            >
              {categories.map(category => (
                <Option key={category.name} value={category.name}>
                  {category.name}
                </Option>
              ))}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select
              placeholder="Difficulty"
              value={selectedDifficulty}
              onChange={setSelectedDifficulty}
              allowClear
              style={{ width: '100%' }}
            >
              <Option value="beginner">Beginner</Option>
              <Option value="intermediate">Intermediate</Option>
              <Option value="advanced">Advanced</Option>
            </Select>
          </Col>
          {(searchTerm || selectedCategory || selectedDifficulty) && (
            <Col>
              <Button
                onClick={() => {
                  setSearchTerm('')
                  setSelectedCategory('')
                  setSelectedDifficulty('')
                }}
              >
                Clear Filters
              </Button>
            </Col>
          )}
        </Row>
      </Card>

      {/* Videos Grid */}
      <div style={{ marginBottom: 16 }}>
        <Text strong>
          {filteredVideos.length} video{filteredVideos.length !== 1 ? 's' : ''} found
        </Text>
      </div>

      {filteredVideos.length === 0 ? (
        <EmptyState
          size="small"
          headingLevel={2}
          type={videos.length === 0 ? 'training' : 'filter'}
          title={videos.length === 0 ? 'No training videos available yet' : 'No matching videos'}
          description={videos.length === 0 ? 'Training content will appear here when it is published.' : 'Try changing your search or filters.'}
        />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredVideos.map((video) => (
            <Col xs={24} sm={12} lg={8} xl={6} key={video.id}>
              <Card
                hoverable
                onClick={() => handleVideoClick(video)}
                cover={
                  <div style={{
                    height: 160,
                    background: 'linear-gradient(135deg, #1890ff 0%, #722ed1 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '48px'
                  }}>
                    <PlayCircleOutlined />
                  </div>
                }
                actions={[
                  <div key="duration" style={{ color: '#666' }}>
                    <ClockCircleOutlined /> {formatDuration(video.duration_minutes)}
                  </div>,
                  <div key="views" style={{ color: '#666' }}>
                    <UserOutlined /> {video.view_count} views
                  </div>
                ]}
              >
                <Card.Meta
                  title={
                    <div>
                      {video.title}
                      <div style={{ float: 'right' }}>
                        <Tag color={getDifficultyColor(video.difficulty_level)}>
                          {video.difficulty_level}
                        </Tag>
                      </div>
                    </div>
                  }
                  description={
                    <div>
                      <Tag
                        color={categories.find(c => c.name === video.category_name)?.color || 'default'}
                        style={{ marginBottom: 8 }}
                      >
                        {video.category_name}
                      </Tag>
                      <Paragraph
                        ellipsis={{ rows: 2, expandable: false }}
                        style={{ margin: 0, fontSize: '12px', color: '#666' }}
                      >
                        {video.description}
                      </Paragraph>
                      <div style={{ marginTop: 8, fontSize: '11px', color: '#999' }}>
                        Created by {video.created_by_name}
                      </div>
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}
        </>
      )}
    </div>
  )
}
