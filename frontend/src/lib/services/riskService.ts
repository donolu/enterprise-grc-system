import { api } from '../api'

export interface RiskCategory {
  id: number
  name: string
  description: string
  color: string
}

export interface RiskMatrix {
  id: number
  name: string
  description: string
  is_default: boolean
  impact_levels: number
  likelihood_levels: number
  matrix_config: Record<string, Record<string, string>>
}

export interface Risk {
  id: number
  risk_id: string
  title: string
  description: string
  category: RiskCategory | null
  impact: number // 1-5 scale
  likelihood: number // 1-5 scale
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  status: 'identified' | 'assessed' | 'treatment_planned' | 'treatment_in_progress' | 'mitigated' | 'accepted' | 'transferred' | 'closed'
  treatment_strategy?: 'mitigate' | 'accept' | 'transfer' | 'avoid'
  treatment_description?: string
  risk_owner: {
    id: number
    username: string
    first_name: string
    last_name: string
    email: string
  } | null
  identified_date: string
  last_assessed_date?: string
  next_review_date?: string
  closed_date?: string
  potential_impact_description?: string
  current_controls?: string
  risk_matrix: RiskMatrix | null
  created_at: string
  updated_at: string
  created_by: {
    id: number
    username: string
    first_name: string
    last_name: string
  } | null
  // Computed properties from Django model
  risk_score: number
  is_overdue_for_review: boolean
  days_until_review: number | null
  is_active: boolean
}

export interface RiskFilters {
  riskLevel?: string[]
  status?: string[]
  category?: string[]
  owner?: string
  dateRange?: [string, string]
  page?: number
  pageSize?: number
  search?: string
}

export interface PaginatedResponse<T> {
  results: T[]
  count: number
  next: string | null
  previous: string | null
}

export const riskService = {
  // Get all risks with optional filtering
  async getRisks(filters: RiskFilters = {}): Promise<PaginatedResponse<Risk>> {
    try {
      const params = new URLSearchParams()
      
      if (filters.riskLevel?.length) {
        params.append('risk_level', filters.riskLevel.join(','))
      }
      if (filters.status?.length) {
        params.append('status', filters.status.join(','))
      }
      if (filters.category?.length) {
        params.append('category', filters.category.join(','))
      }
      if (filters.owner) {
        params.append('owner', filters.owner)
      }
      if (filters.search) {
        params.append('search', filters.search)
      }
      if (filters.dateRange) {
        params.append('date_from', filters.dateRange[0])
        params.append('date_to', filters.dateRange[1])
      }
      if (filters.page) {
        params.append('page', filters.page.toString())
      }
      if (filters.pageSize) {
        params.append('page_size', filters.pageSize.toString())
      }

      const response = await api.get(`/risk/risks/?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error fetching risks:', error)
      throw error // Let the calling component handle the error
    }
  },

  // Get single risk by ID
  async getRisk(id: string | number): Promise<Risk> {
    try {
      const response = await api.get(`/risk/risks/${id}/`)
      return response.data
    } catch (error) {
      console.error('Error fetching risk:', error)
      throw error
    }
  },

  // Create new risk
  async createRisk(riskData: Partial<Risk>): Promise<Risk> {
    try {
      const response = await api.post('/risk/risks/', riskData)
      return response.data
    } catch (error) {
      console.error('Error creating risk:', error)
      throw error
    }
  },

  // Update risk
  async updateRisk(id: string | number, riskData: Partial<Risk>): Promise<Risk> {
    try {
      const response = await api.patch(`/risk/risks/${id}/`, riskData)
      return response.data
    } catch (error) {
      console.error('Error updating risk:', error)
      throw error
    }
  },

  // Delete risk
  async deleteRisk(id: string | number): Promise<void> {
    try {
      await api.delete(`/risk/risks/${id}/`)
    } catch (error) {
      console.error('Error deleting risk:', error)
      throw error
    }
  },

  // Get risk analytics
  async getRiskAnalytics() {
    try {
      const response = await api.get('/risk/analytics/dashboard/')
      return response.data
    } catch (error) {
      console.error('Error fetching risk analytics:', error)
      throw error // Let the calling component handle the error
    }
  },

  // Get risk categories
  async getRiskCategories(): Promise<RiskCategory[]> {
    try {
      const response = await api.get('/risk/categories/')
      return response.data.results || response.data
    } catch (error) {
      console.error('Error fetching risk categories:', error)
      return [
        { id: 1, name: 'Cybersecurity', description: 'Information security related risks', color: '#DC2626' },
        { id: 2, name: 'Compliance', description: 'Regulatory compliance risks', color: '#F59E0B' },
        { id: 3, name: 'Operational', description: 'Business operational risks', color: '#3B82F6' }
      ]
    }
  },

  // Get risk matrices
  async getRiskMatrices(): Promise<RiskMatrix[]> {
    try {
      const response = await api.get('/risk/matrices/')
      return response.data.results || response.data
    } catch (error) {
      console.error('Error fetching risk matrices:', error)
      return []
    }
  },

  // Get risk choices (status, levels, etc.) from Django
  async getRiskChoices(): Promise<{
    risk_levels: Array<{value: string, label: string}>,
    status_choices: Array<{value: string, label: string}>,
    treatment_strategies: Array<{value: string, label: string}>
  }> {
    try {
      const response = await api.get('/risk/choices/')
      return response.data
    } catch (error) {
      console.error('Error fetching risk choices:', error)
      return {
        risk_levels: [
          { value: 'low', label: 'Low' },
          { value: 'medium', label: 'Medium' },
          { value: 'high', label: 'High' },
          { value: 'critical', label: 'Critical' }
        ],
        status_choices: [
          { value: 'identified', label: 'Identified' },
          { value: 'assessed', label: 'Assessed' },
          { value: 'treatment_planned', label: 'Treatment Planned' },
          { value: 'treatment_in_progress', label: 'Treatment in Progress' },
          { value: 'mitigated', label: 'Mitigated' },
          { value: 'accepted', label: 'Accepted' },
          { value: 'transferred', label: 'Transferred' },
          { value: 'closed', label: 'Closed' }
        ],
        treatment_strategies: [
          { value: 'mitigate', label: 'Mitigate' },
          { value: 'accept', label: 'Accept' },
          { value: 'transfer', label: 'Transfer' },
          { value: 'avoid', label: 'Avoid' }
        ]
      }
    }
  }
}

export default riskService