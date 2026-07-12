import { api } from '../api'

export interface PolicyCategory {
  id: string
  name: string
  description: string
  color: string
  created_at: string
  updated_at: string
}

export interface PolicyVersion {
  id: string
  version_number: string
  document_url?: string
  changelog: string
  file_size?: number
  file_name?: string
  is_active: boolean
  effective_date: string
  expiry_date?: string
  created_at: string
  created_by: {
    id: number
    username: string
    first_name: string
    last_name: string
  }
}

export interface Policy {
  id: string
  policy_code: string
  title: string
  category: PolicyCategory
  policy_type: 'procedure' | 'policy' | 'standard' | 'guideline' | 'framework'
  status: 'draft' | 'under_review' | 'approved' | 'archived'
  owner: {
    id: number
    username: string
    first_name: string
    last_name: string
    email: string
  }
  approver?: {
    id: number
    username: string
    first_name: string
    last_name: string
    email: string
  } | null
  review_frequency_months: number
  next_review_date?: string
  requires_acknowledgment: boolean
  acknowledgment_validity_days: number
  current_version: PolicyVersion | null
  latest_version: PolicyVersion | null
  is_due_for_review: boolean
  created_at: string
  updated_at: string
  created_by: {
    id: number
    username: string
    first_name: string
    last_name: string
  } | null
}

export interface PolicyAcknowledgment {
  id: number
  user: {
    id: number
    username: string
    first_name: string
    last_name: string
    email: string
  }
  policy_version: PolicyVersion
  acknowledged_at: string
  ip_address: string
  user_agent: string
  is_valid: boolean
  expires_at: string
}

export interface PolicyDistribution {
  id: number
  policy: Policy
  target_users: number[]
  target_groups: number[]
  due_date?: string
  reminder_frequency_days: number
  is_mandatory: boolean
  created_at: string
  created_by: {
    id: number
    username: string
    first_name: string
    last_name: string
  }
  is_overdue: boolean
  completion_percentage: number
}

export interface PolicyFilters {
  status?: string[]
  category?: string[]
  policy_type?: string[]
  owner?: string
  due_for_review?: boolean
  requires_acknowledgment?: boolean
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

export const policyService = {
  // Get all policies with optional filtering
  async getPolicies(filters: PolicyFilters = {}): Promise<PaginatedResponse<Policy>> {
    try {
      const params = new URLSearchParams()
      
      if (filters.status?.length) {
        params.append('status', filters.status.join(','))
      }
      if (filters.category?.length) {
        params.append('category', filters.category.join(','))
      }
      if (filters.policy_type?.length) {
        params.append('policy_type', filters.policy_type.join(','))
      }
      if (filters.owner) {
        params.append('owner', filters.owner)
      }
      if (filters.due_for_review !== undefined) {
        params.append('due_for_review', filters.due_for_review.toString())
      }
      if (filters.requires_acknowledgment !== undefined) {
        params.append('requires_acknowledgment', filters.requires_acknowledgment.toString())
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

      const response = await api.get(`/policies/policies/?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error fetching policies:', error)
      
      // Return mock data as fallback with Django model structure
      return {
        results: [
          {
            id: '550e8400-e29b-41d4-a716-446655440000',
            policy_code: 'POL-SEC-001',
            title: 'Information Security Policy',
            category: {
              id: '550e8400-e29b-41d4-a716-446655440001',
              name: 'Security',
              description: 'Information security policies and procedures',
              color: '#dc2626',
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:00:00Z'
            },
            policy_type: 'policy',
            status: 'approved',
            owner: {
              id: 1,
              username: 'security.manager',
              first_name: 'Security',
              last_name: 'Manager',
              email: 'security@company.com'
            },
            approver: {
              id: 2,
              username: 'ciso',
              first_name: 'Chief',
              last_name: 'Security Officer',
              email: 'ciso@company.com'
            },
            review_frequency_months: 12,
            next_review_date: '2025-06-01',
            requires_acknowledgment: true,
            acknowledgment_validity_days: 365,
            current_version: {
              id: '550e8400-e29b-41d4-a716-446655440010',
              version_number: '2.1',
              document_url: '/media/policies/security-policy-v2.1.pdf',
              changelog: 'Updated encryption requirements and access controls',
              file_size: 2458432,
              file_name: 'ISP-001_Version_2.1.pdf',
              is_active: true,
              effective_date: '2024-06-01',
              expiry_date: '2025-06-01',
              created_at: '2024-06-01T00:00:00Z',
              created_by: {
                id: 1,
                username: 'security.manager',
                first_name: 'Security',
                last_name: 'Manager'
              }
            },
            latest_version: {
              id: '550e8400-e29b-41d4-a716-446655440010',
              version_number: '2.1',
              document_url: '/media/policies/security-policy-v2.1.pdf',
              changelog: 'Updated encryption requirements and access controls',
              file_size: 2458432,
              file_name: 'ISP-001_Version_2.1.pdf',
              is_active: true,
              effective_date: '2024-06-01',
              expiry_date: '2025-06-01',
              created_at: '2024-06-01T00:00:00Z',
              created_by: {
                id: 1,
                username: 'security.manager',
                first_name: 'Security',
                last_name: 'Manager'
              }
            },
            is_due_for_review: false,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-06-01T10:30:00Z',
            created_by: {
              id: 1,
              username: 'admin',
              first_name: 'Admin',
              last_name: 'User'
            }
          }
        ],
        count: 1,
        next: null,
        previous: null
      }
    }
  },

  // Get single policy by ID
  async getPolicy(id: string): Promise<Policy> {
    try {
      const response = await api.get(`/policies/policies/${id}/`)
      return response.data
    } catch (error) {
      console.error('Error fetching policy:', error)
      throw error
    }
  },

  // Create new policy
  async createPolicy(policyData: Partial<Policy>): Promise<Policy> {
    try {
      const response = await api.post('/policies/policies/', policyData)
      return response.data
    } catch (error) {
      console.error('Error creating policy:', error)
      throw error
    }
  },

  // Update policy
  async updatePolicy(id: string, policyData: Partial<Policy>): Promise<Policy> {
    try {
      const response = await api.patch(`/policies/policies/${id}/`, policyData)
      return response.data
    } catch (error) {
      console.error('Error updating policy:', error)
      throw error
    }
  },

  // Delete policy
  async deletePolicy(id: string): Promise<void> {
    try {
      await api.delete(`/policies/policies/${id}/`)
    } catch (error) {
      console.error('Error deleting policy:', error)
      throw error
    }
  },

  // Get policy categories
  async getPolicyCategories(): Promise<PolicyCategory[]> {
    try {
      const response = await api.get('/policies/categories/')
      return response.data.results || response.data
    } catch (error) {
      console.error('Error fetching policy categories:', error)
      return [
        {
          id: '550e8400-e29b-41d4-a716-446655440001',
          name: 'Security',
          description: 'Information security policies and procedures',
          color: '#dc2626',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '550e8400-e29b-41d4-a716-446655440002',
          name: 'HR',
          description: 'Human resources policies and procedures',
          color: '#059669',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '550e8400-e29b-41d4-a716-446655440003',
          name: 'IT',
          description: 'Information technology policies and procedures',
          color: '#2563eb',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ]
    }
  },

  // Get policy acknowledgments
  async getPolicyAcknowledgments(policyId?: string): Promise<PaginatedResponse<PolicyAcknowledgment>> {
    try {
      const params = new URLSearchParams()
      if (policyId) {
        params.append('policy', policyId)
      }
      
      const response = await api.get(`/policies/acknowledgments/?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error fetching policy acknowledgments:', error)
      return {
        results: [],
        count: 0,
        next: null,
        previous: null
      }
    }
  },

  // Create policy acknowledgment
  async acknowledgePolicy(policyVersionId: string): Promise<PolicyAcknowledgment> {
    try {
      const response = await api.post('/policies/acknowledgments/', {
        policy_version: policyVersionId
      })
      return response.data
    } catch (error) {
      console.error('Error creating policy acknowledgment:', error)
      throw error
    }
  },

  // Get policy distributions
  async getPolicyDistributions(): Promise<PaginatedResponse<PolicyDistribution>> {
    try {
      const response = await api.get('/policies/distributions/')
      return response.data
    } catch (error) {
      console.error('Error fetching policy distributions:', error)
      return {
        results: [],
        count: 0,
        next: null,
        previous: null
      }
    }
  },

  // Get policy analytics
  async getPolicyAnalytics() {
    try {
      const response = await api.get('/policies/analytics/dashboard/')
      return response.data
    } catch (error) {
      console.error('Error fetching policy analytics:', error)
      
      // Return mock analytics as fallback
      return {
        totalPolicies: 24,
        pendingAcknowledgments: 45,
        overdueReviews: 3,
        complianceRate: 92.5,
        acknowledgmentTrend: 5.8
      }
    }
  },

  // Get policy choices (status, types, etc.) from Django
  async getPolicyChoices(): Promise<{
    status_choices: Array<{value: string, label: string}>,
    policy_type_choices: Array<{value: string, label: string}>
  }> {
    try {
      const response = await api.get('/policies/choices/')
      return response.data
    } catch (error) {
      console.error('Error fetching policy choices:', error)
      return {
        status_choices: [
          { value: 'draft', label: 'Draft' },
          { value: 'under_review', label: 'Under Review' },
          { value: 'approved', label: 'Approved' },
          { value: 'archived', label: 'Archived' }
        ],
        policy_type_choices: [
          { value: 'procedure', label: 'Procedure' },
          { value: 'policy', label: 'Policy' },
          { value: 'standard', label: 'Standard' },
          { value: 'guideline', label: 'Guideline' },
          { value: 'framework', label: 'Framework' }
        ]
      }
    }
  }
}

export default policyService