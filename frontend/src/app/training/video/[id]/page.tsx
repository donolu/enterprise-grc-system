'use client'

import React, { useEffect, useState, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Card, Typography, Button, Tag, Row, Col, Progress, message, Spin } from 'antd'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  ClockCircleOutlined,
  UserOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'
import { api } from '@/lib/api'

const { Title, Text, Paragraph } = Typography

interface TrainingVideo {
  id: string
  title: string
  description: string
  category_details: {
    name: string
    color: string
  }
  video_provider: string
  video_url: string
  embed_url: string
  duration_minutes: number | null
  difficulty_level: string
  view_count: number
  created_by_details: {
    name: string
    email: string
  }
  created_at: string
}

export default function VideoPlayerPage() {
  const params = useParams()
  const router = useRouter()
  const [video, setVideo] = useState<TrainingVideo | null>(null)
  const [loading, setLoading] = useState(true)
  const [watchProgress, setWatchProgress] = useState(0)
  const [isCompleted, setIsCompleted] = useState(false)
  const [viewStartTime, setViewStartTime] = useState<Date | null>(null)
  const progressInterval = useRef<NodeJS.Timeout | null>(null)

  const videoId = params.id as string

  useEffect(() => {
    if (videoId) {
      fetchVideo()
    }

    return () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current)
      }

      // Track final view when component unmounts
      if (video && viewStartTime) {
        trackVideoView(false)
      }
    }
  }, [videoId])

  const fetchVideo = async () => {
    try {
      setLoading(true)
      const response = await api.get(`/api/training/videos/${videoId}/`)
      setVideo(response.data)
      setViewStartTime(new Date())

      // Start tracking progress every 10 seconds
      progressInterval.current = setInterval(() => {
        setWatchProgress(prev => {
          const newProgress = Math.min(prev + 10, 100)

          // Mark as completed when reaching 80% or more
          if (newProgress >= 80 && !isCompleted) {
            setIsCompleted(true)
            trackVideoView(true)
          }

          return newProgress
        })
      }, 10000) // Update every 10 seconds

    } catch (error) {
      console.error('Failed to fetch video:', error)
      message.error('Failed to load video')
      router.push('/training')
    } finally {
      setLoading(false)
    }
  }

  const trackVideoView = async (completed: boolean) => {
    if (!video || !viewStartTime) return

    const durationWatched = Math.floor((new Date().getTime() - viewStartTime.getTime()) / 1000)

    try {
      await api.post(`/api/training/videos/${video.id}/track_view/`, {
        duration_watched: durationWatched,
        completed,
        completion_percentage: watchProgress
      })
    } catch (error) {
      console.error('Failed to track video view:', error)
    }
  }

  const handleVideoLoad = () => {
    // Called when video iframe loads
    message.success('Video loaded successfully')
  }

  const handleMarkComplete = () => {
    setIsCompleted(true)
    setWatchProgress(100)
    trackVideoView(true)
    message.success('Video marked as completed!')
  }

  const getDifficultyColor = (level: string) => {
    switch (level) {
      case 'beginner': return 'green'
      case 'intermediate': return 'orange'
      case 'advanced': return 'red'
      default: return 'default'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const formatDuration = (minutes: number | null) => {
    if (!minutes) return 'Duration not specified'
    if (minutes < 60) return `${minutes} minutes`
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return `${hours} hour${hours !== 1 ? 's' : ''} ${remainingMinutes} minute${remainingMinutes !== 1 ? 's' : ''}`
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading video...</div>
      </div>
    )
  }

  if (!video) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Text>Video not found</Text>
      </div>
    )
  }

  return (
    <div>
      {/* Navigation */}
      <div style={{ marginBottom: 24 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => router.push('/training')}
          size="large"
        >
          Back to Training
        </Button>
      </div>

      <Row gutter={[24, 24]}>
        {/* Video Player */}
        <Col xs={24} lg={16}>
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Title level={3}>{video.title}</Title>
              <div style={{ marginBottom: 16 }}>
                <Tag
                  color={video.category_details.color}
                  style={{ marginRight: 8 }}
                >
                  {video.category_details.name}
                </Tag>
                <Tag color={getDifficultyColor(video.difficulty_level)}>
                  {video.difficulty_level}
                </Tag>
                {isCompleted && (
                  <Tag color="green" style={{ marginLeft: 8 }}>
                    <CheckCircleOutlined /> Completed
                  </Tag>
                )}
              </div>
            </div>

            {/* Video Embed */}
            <div
              style={{
                position: 'relative',
                paddingBottom: '56.25%', // 16:9 aspect ratio
                height: 0,
                overflow: 'hidden',
                marginBottom: 16
              }}
            >
              {video.video_provider === 'synthesia' ? (
                // Synthesia.io embed
                <iframe
                  src={video.embed_url}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: 'none'
                  }}
                  allowFullScreen
                  onLoad={handleVideoLoad}
                  title={video.title}
                />
              ) : video.video_provider === 'youtube' ? (
                // YouTube embed
                <iframe
                  src={video.embed_url}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: 'none'
                  }}
                  allowFullScreen
                  onLoad={handleVideoLoad}
                  title={video.title}
                />
              ) : video.video_provider === 'vimeo' ? (
                // Vimeo embed
                <iframe
                  src={video.embed_url}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: 'none'
                  }}
                  allowFullScreen
                  onLoad={handleVideoLoad}
                  title={video.title}
                />
              ) : (
                // Fallback for custom URLs
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  backgroundColor: '#f0f0f0',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#666'
                }}>
                  <PlayCircleOutlined style={{ fontSize: '64px', marginBottom: 16 }} />
                  <Text>Custom video player not available</Text>
                  <Button
                    type="primary"
                    href={video.video_url}
                    target="_blank"
                    style={{ marginTop: 16 }}
                  >
                    Open Video in New Tab
                  </Button>
                </div>
              )}
            </div>

            {/* Progress Tracking */}
            <Card style={{ backgroundColor: '#f8f9fa' }}>
              <div style={{ marginBottom: 8 }}>
                <Text strong>Watch Progress</Text>
                {!isCompleted && (
                  <Button
                    type="link"

                    onClick={handleMarkComplete}
                    style={{ float: 'right' }}
                  >
                    Mark as Complete
                  </Button>
                )}
              </div>
              <Progress
                percent={watchProgress}
                status={isCompleted ? 'success' : 'active'}

              />
              {isCompleted && (
                <div style={{ marginTop: 8, color: '#52c41a' }}>
                  <CheckCircleOutlined /> Congratulations! You've completed this training video.
                </div>
              )}
            </Card>
          </Card>
        </Col>

        {/* Video Information */}
        <Col xs={24} lg={8}>
          <Card title={<span><InfoCircleOutlined /> Video Information</span>}>
            <div style={{ marginBottom: 16 }}>
              <Text strong>Description</Text>
              <Paragraph style={{ marginTop: 8 }}>
                {video.description}
              </Paragraph>
            </div>

            <div style={{ marginBottom: 16 }}>
              <Row gutter={[16, 8]}>
                <Col span={12}>
                  <Text type="secondary">Duration:</Text>
                  <div>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    {formatDuration(video.duration_minutes)}
                  </div>
                </Col>
                <Col span={12}>
                  <Text type="secondary">Views:</Text>
                  <div>
                    <UserOutlined style={{ marginRight: 4 }} />
                    {video.view_count}
                  </div>
                </Col>
                <Col span={12}>
                  <Text type="secondary">Difficulty:</Text>
                  <div>
                    <Tag color={getDifficultyColor(video.difficulty_level)}>
                      {video.difficulty_level}
                    </Tag>
                  </div>
                </Col>
                <Col span={12}>
                  <Text type="secondary">Provider:</Text>
                  <div style={{ textTransform: 'capitalize' }}>
                    {video.video_provider}
                  </div>
                </Col>
              </Row>
            </div>

            <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
              <Text type="secondary">Created by:</Text>
              <div style={{ marginTop: 4 }}>
                <Text strong>{video.created_by_details.name}</Text>
                <br />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {formatDate(video.created_at)}
                </Text>
              </div>
            </div>
          </Card>

          {/* Additional Actions */}
          <Card title="Actions" style={{ marginTop: 16 }}>
            <div style={{ textAlign: 'center' }}>
              <Button
                type="primary"
                size="large"
                onClick={() => router.push('/training')}
                style={{ width: '100%' }}
              >
                Browse More Videos
              </Button>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}