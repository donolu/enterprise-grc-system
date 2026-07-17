'use client'

import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Button, Select, Input, Tag, Empty, Spin, message } from 'antd'
import { PlayCircleOutlined, SearchOutlined, FilterOutlined, ClockCircleOutlined, UserOutlined } from '@ant-design/icons'
import { api } from '@/lib/api'

const { Title, Text, Paragraph } = Typography
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
  const [videos, setVideos] = useState<TrainingVideo[]>([])
  const [categories, setCategories] = useState<TrainingCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)

      // Mock data for development
      const mockCategories = [
        {
          id: '1',
          name: 'Security Awareness',
          description: 'General security awareness training',
          color: '#f5222d',
          videos_count: 12
        },
        {
          id: '2',
          name: 'Phishing Prevention',
          description: 'How to identify and avoid phishing attacks',
          color: '#fa8c16',
          videos_count: 8
        },
        {
          id: '3',
          name: 'Data Protection',
          description: 'Data handling and privacy best practices',
          color: '#1890ff',
          videos_count: 15
        },
        {
          id: '4',
          name: 'Incident Response',
          description: 'How to respond to security incidents',
          color: '#722ed1',
          videos_count: 10
        }
      ]

      const mockVideos = [
        {
          id: '1',
          title: 'Introduction to Cybersecurity',
          description: 'Learn the fundamentals of cybersecurity and why it matters for every employee.',
          category_name: 'Security Awareness',
          category_color: '#f5222d',
          video_provider: 'internal',
          duration_minutes: 15,
          difficulty_level: 'beginner',
          view_count: 234,
          created_by_name: 'Security Team',
          created_at: '2024-08-01T10:00:00Z'
        },
        {
          id: '2',
          title: 'Spotting Phishing Emails',
          description: 'Learn to identify common phishing techniques and protect yourself from email-based attacks.',
          category_name: 'Phishing Prevention',
          category_color: '#fa8c16',
          video_provider: 'internal',
          duration_minutes: 22,
          difficulty_level: 'intermediate',
          view_count: 189,
          created_by_name: 'Training Team',
          created_at: '2024-07-28T14:30:00Z'
        },
        {
          id: '3',
          title: 'Password Security Best Practices',
          description: 'Create strong passwords and use multi-factor authentication to secure your accounts.',
          category_name: 'Security Awareness',
          category_color: '#f5222d',
          video_provider: 'internal',
          duration_minutes: 18,
          difficulty_level: 'beginner',
          view_count: 312,
          created_by_name: 'Security Team',
          created_at: '2024-07-25T09:15:00Z'
        },
        {
          id: '4',
          title: 'Data Classification Guidelines',
          description: 'Understand how to properly classify and handle sensitive organizational data.',
          category_name: 'Data Protection',
          category_color: '#1890ff',
          video_provider: 'internal',
          duration_minutes: 28,
          difficulty_level: 'intermediate',
          view_count: 156,
          created_by_name: 'Compliance Team',
          created_at: '2024-07-20T11:45:00Z'
        }
      ]

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 700))

      // Try to fetch from API first, fallback to mock data
      try {
        const [videosResponse, categoriesResponse] = await Promise.all([
          api.get('/training/videos/'),
          api.get('/training/categories/')
        ])

        setVideos(videosResponse.data.results || videosResponse.data)
        setCategories(categoriesResponse.data.results || categoriesResponse.data)
      } catch (apiError) {
        console.log('API not available, using mock data:', apiError)
        setVideos(mockVideos)
        setCategories(mockCategories)
      }
    } catch (error) {
      console.error('Failed to fetch training data:', error)
      message.error('Backend not available - showing demo data')
    } finally {
      setLoading(false)
    }
  }

  const handleVideoClick = (video: TrainingVideo) => {
    // Track video view
    trackVideoView(video.id)

    // Navigate to video player page
    window.location.href = `/training/video/${video.id}`
  }

  const trackVideoView = async (videoId: string) => {
    try {
      await api.post(`/training/videos/${videoId}/track_view/`, {
        duration_watched: 0,
        completed: false,
        completion_percentage: 0
      })
    } catch (error) {
      console.error('Failed to track video view:', error)
    }
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
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading training content...</div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <PlayCircleOutlined style={{ marginRight: 8 }} />
          Security Training Videos
        </Title>
        <Text type="secondary">
          Enhance your security awareness with our comprehensive training library
        </Text>
      </div>

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
        <Card>
          <Empty
            description={
              videos.length === 0
                ? "No training videos available yet"
                : "No videos match your current filters"
            }
          />
        </Card>
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
    </div>
  )
}
