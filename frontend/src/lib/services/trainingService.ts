import { api } from '../api'

export interface TrainingCategory {
  id: string
  name: string
  description: string
  color: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TrainingVideo {
  id: string
  title: string
  description: string
  category: TrainingCategory
  video_provider: 'synthesia' | 'youtube' | 'vimeo' | 'custom'
  video_url: string
  video_id: string
  duration_minutes?: number
  difficulty_level: 'beginner' | 'intermediate' | 'advanced'
  is_published: boolean
  published_at?: string
  created_by: {
    id: number
    username: string
    first_name: string
    last_name: string
  }
  view_count: number
  created_at: string
  updated_at: string
}

export interface SecurityAwarenessCampaign {
  id: string
  name: string
  description: string
  start_date: string
  end_date: string
  status: 'draft' | 'active' | 'completed' | 'paused'
  target_audience: {
    include_all_users: boolean
    include_new_users: boolean
    specific_users: number[]
    exclude_users: number[]
    department_filters: string[]
    role_filters: string[]
  }
  training_videos: string[]
  completion_deadline?: string
  reminder_frequency_days: number
  max_reminders: number
  created_by: {
    id: number
    username: string
    first_name: string
    last_name: string
  }
  created_at: string
  updated_at: string
  // Computed fields
  total_target_users: number
  completion_rate: number
  is_active: boolean
  is_overdue: boolean
}

export interface CampaignDelivery {
  id: string
  campaign: SecurityAwarenessCampaign
  user: {
    id: number
    username: string
    first_name: string
    last_name: string
    email: string
  }
  assigned_at: string
  first_email_sent?: string
  last_reminder_sent?: string
  completed_at?: string
  completion_percentage: number
  reminders_sent: number
  status: 'assigned' | 'in_progress' | 'completed' | 'overdue'
  is_overdue: boolean
  days_since_assignment: number
  videos_watched: number
  total_videos: number
}

export interface VideoView {
  id: string
  video: TrainingVideo
  user: {
    id: number
    username: string
    first_name: string
    last_name: string
  }
  campaign_delivery?: string
  watched_at: string
  watch_duration_seconds?: number
  completion_percentage: number
  ip_address: string
  user_agent: string
}

export interface TrainingDashboard {
  summary_metrics: {
    total_videos: number
    active_campaigns: number
    total_completions: number
    average_completion_rate: number
  }
  completion_trends: {
    labels: string[]
    datasets: Array<{
      label: string
      data: number[]
      backgroundColor?: string
      borderColor?: string
    }>
  }
  category_performance: {
    labels: string[]
    datasets: Array<{
      label: string
      data: number[]
      backgroundColor?: string[]
    }>
  }
  recent_activities: Array<{
    id: string
    type: 'video_watched' | 'campaign_started' | 'campaign_completed'
    user: string
    video_title?: string
    campaign_name?: string
    timestamp: string
  }>
}

export interface TrainingFilters {
  category?: string[]
  difficulty_level?: string[]
  is_published?: boolean
  video_provider?: string[]
  search?: string
  page?: number
  pageSize?: number
}

export interface CampaignFilters {
  status?: string[]
  start_date_from?: string
  start_date_to?: string
  created_by?: number
  search?: string
  page?: number
  pageSize?: number
}

export interface PaginatedResponse<T> {
  results: T[]
  count: number
  next: string | null
  previous: string | null
}

export const trainingService = {
  // Training Videos
  async getTrainingVideos(filters: TrainingFilters = {}): Promise<PaginatedResponse<TrainingVideo>> {
    try {
      const params = new URLSearchParams()
      
      if (filters.category?.length) {
        params.append('category', filters.category.join(','))
      }
      if (filters.difficulty_level?.length) {
        params.append('difficulty_level', filters.difficulty_level.join(','))
      }
      if (filters.is_published !== undefined) {
        params.append('is_published', filters.is_published.toString())
      }
      if (filters.video_provider?.length) {
        params.append('video_provider', filters.video_provider.join(','))
      }
      if (filters.search) {
        params.append('search', filters.search)
      }
      if (filters.page) {
        params.append('page', filters.page.toString())
      }
      if (filters.pageSize) {
        params.append('page_size', filters.pageSize.toString())
      }

      const response = await api.get(`/training/videos/?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error fetching training videos:', error)
      
      // Return mock data as fallback
      return {
        results: [
          {
            id: '550e8400-e29b-41d4-a716-446655440000',
            title: 'Phishing Awareness Training',
            description: 'Learn to identify and avoid phishing attacks',
            category: {
              id: '550e8400-e29b-41d4-a716-446655440010',
              name: 'Email Security',
              description: 'Training focused on email security best practices',
              color: '#ef4444',
              is_active: true,
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:00:00Z'
            },
            video_provider: 'synthesia',
            video_url: 'https://share.synthesia.io/example-video',
            video_id: 'synthesia-123',
            duration_minutes: 15,
            difficulty_level: 'beginner',
            is_published: true,
            published_at: '2024-06-01T00:00:00Z',
            created_by: {
              id: 1,
              username: 'training.admin',
              first_name: 'Training',
              last_name: 'Admin'
            },
            view_count: 1247,
            created_at: '2024-05-15T00:00:00Z',
            updated_at: '2024-08-20T10:30:00Z'
          }
        ],
        count: 1,
        next: null,
        previous: null
      }
    }
  },

  // Get single training video
  async getTrainingVideo(id: string): Promise<TrainingVideo> {
    try {
      const response = await api.get(`/training/videos/${id}/`)
      return response.data
    } catch (error) {
      console.error('Error fetching training video:', error)
      throw error
    }
  },

  // Create training video
  async createTrainingVideo(videoData: Partial<TrainingVideo>): Promise<TrainingVideo> {
    try {
      const response = await api.post('/training/videos/', videoData)
      return response.data
    } catch (error) {
      console.error('Error creating training video:', error)
      throw error
    }
  },

  // Update training video
  async updateTrainingVideo(id: string, videoData: Partial<TrainingVideo>): Promise<TrainingVideo> {
    try {
      const response = await api.patch(`/training/videos/${id}/`, videoData)
      return response.data
    } catch (error) {
      console.error('Error updating training video:', error)
      throw error
    }
  },

  // Delete training video
  async deleteTrainingVideo(id: string): Promise<void> {
    try {
      await api.delete(`/training/videos/${id}/`)
    } catch (error) {
      console.error('Error deleting training video:', error)
      throw error
    }
  },

  // Training Categories
  async getTrainingCategories(): Promise<TrainingCategory[]> {
    try {
      const response = await api.get('/training/categories/')
      return response.data.results || response.data
    } catch (error) {
      console.error('Error fetching training categories:', error)
      return [
        {
          id: '550e8400-e29b-41d4-a716-446655440010',
          name: 'Email Security',
          description: 'Training focused on email security best practices',
          color: '#ef4444',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '550e8400-e29b-41d4-a716-446655440011',
          name: 'Password Security',
          description: 'Best practices for password creation and management',
          color: '#10b981',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ]
    }
  },

  // Security Awareness Campaigns
  async getCampaigns(filters: CampaignFilters = {}): Promise<PaginatedResponse<SecurityAwarenessCampaign>> {
    try {
      const params = new URLSearchParams()
      
      if (filters.status?.length) {
        params.append('status', filters.status.join(','))
      }
      if (filters.start_date_from) {
        params.append('start_date_from', filters.start_date_from)
      }
      if (filters.start_date_to) {
        params.append('start_date_to', filters.start_date_to)
      }
      if (filters.created_by) {
        params.append('created_by', filters.created_by.toString())
      }
      if (filters.search) {
        params.append('search', filters.search)
      }
      if (filters.page) {
        params.append('page', filters.page.toString())
      }
      if (filters.pageSize) {
        params.append('page_size', filters.pageSize.toString())
      }

      const response = await api.get(`/training/campaigns/?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error fetching campaigns:', error)
      
      return {
        results: [],
        count: 0,
        next: null,
        previous: null
      }
    }
  },

  // Create campaign
  async createCampaign(campaignData: Partial<SecurityAwarenessCampaign>): Promise<SecurityAwarenessCampaign> {
    try {
      const response = await api.post('/training/campaigns/', campaignData)
      return response.data
    } catch (error) {
      console.error('Error creating campaign:', error)
      throw error
    }
  },

  // Record video view
  async recordVideoView(videoId: string, campaignDeliveryId?: string): Promise<VideoView> {
    try {
      const response = await api.post('/training/views/', {
        video: videoId,
        campaign_delivery: campaignDeliveryId
      })
      return response.data
    } catch (error) {
      console.error('Error recording video view:', error)
      throw error
    }
  },

  // Get training dashboard
  async getTrainingDashboard(): Promise<TrainingDashboard> {
    try {
      const response = await api.get('/training/dashboard/')
      return response.data
    } catch (error) {
      console.error('Error fetching training dashboard:', error)
      
      return {
        summary_metrics: {
          total_videos: 24,
          active_campaigns: 3,
          total_completions: 1247,
          average_completion_rate: 87.3
        },
        completion_trends: {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
          datasets: [{
            label: 'Completion Rate',
            data: [82, 85, 88, 87, 89, 87],
            borderColor: '#10b981'
          }]
        },
        category_performance: {
          labels: ['Email Security', 'Password Security', 'Social Engineering'],
          datasets: [{
            label: 'Completion Rate',
            data: [95, 88, 82],
            backgroundColor: ['#ef4444', '#10b981', '#f59e0b']
          }]
        },
        recent_activities: [
          {
            id: '1',
            type: 'video_watched',
            user: 'john.smith',
            video_title: 'Phishing Awareness Training',
            timestamp: '2024-08-25T10:30:00Z'
          }
        ]
      }
    }
  },

  // Get training choices from Django
  async getTrainingChoices(): Promise<{
    video_providers: Array<{value: string, label: string}>,
    difficulty_levels: Array<{value: string, label: string}>,
    campaign_statuses: Array<{value: string, label: string}>
  }> {
    try {
      const response = await api.get('/training/choices/')
      return response.data
    } catch (error) {
      console.error('Error fetching training choices:', error)
      return {
        video_providers: [
          { value: 'synthesia', label: 'Synthesia.io' },
          { value: 'youtube', label: 'YouTube' },
          { value: 'vimeo', label: 'Vimeo' },
          { value: 'custom', label: 'Custom URL' }
        ],
        difficulty_levels: [
          { value: 'beginner', label: 'Beginner' },
          { value: 'intermediate', label: 'Intermediate' },
          { value: 'advanced', label: 'Advanced' }
        ],
        campaign_statuses: [
          { value: 'draft', label: 'Draft' },
          { value: 'active', label: 'Active' },
          { value: 'completed', label: 'Completed' },
          { value: 'paused', label: 'Paused' }
        ]
      }
    }
  }
}

export default trainingService