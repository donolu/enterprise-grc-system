import { api } from '../api'

export interface VendorCategory {
  id: number
  name: string
  description: string
  color_code: string
  risk_weight: 'low' | 'medium' | 'high' | 'critical'
  compliance_requirements: Record<string, unknown>
}

export interface VendorContact {
  id: number
  vendor: number
  contact_type: 'primary' | 'billing' | 'technical' | 'legal' | 'emergency'
  first_name: string
  last_name: string
  title: string
  email: string
  phone: string
  is_primary: boolean
}

export interface Vendor {
  id: number
  vendor_id: string
  name: string
  legal_name: string
  category: VendorCategory | null
  business_description: string
  website: string
  tax_id: string
  duns_number: string
  address_line1: string
  address_line2: string
  city: string
  state_province: string
  postal_code: string
  country: string
  status: 'active' | 'inactive' | 'under_review' | 'approved' | 'suspended' | 'terminated'
  vendor_type: 'supplier' | 'service_provider' | 'consultant' | 'contractor' | 'partner' | 'subcontractor'
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  risk_score: number | null
  annual_spend: number | null
  credit_rating: string
  payment_terms: string
  operating_regions: string[]
  primary_region: string
  custom_fields: Record<string, unknown>
  certifications: string[]
  compliance_status: Record<string, unknown>
  data_processing_agreement: boolean
  security_assessment_completed: boolean
  security_assessment_date: string | null
  assigned_to: {
    id: number
    username: string
    first_name: string
    last_name: string
    email: string
  } | null
  relationship_start_date: string | null
  created_at: string
  updated_at: string
  created_by: {
    id: number
    username: string
    first_name: string
    last_name: string
  } | null
}

export interface VendorFilters {
  riskLevel?: string
  status?: string[]
  category?: string[]
  spend?: string
  contractExpiry?: string
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

export const vendorService = {
  // Get all vendors with optional filtering
  async getVendors(filters: VendorFilters = {}): Promise<PaginatedResponse<Vendor>> {
    try {
      const params = new URLSearchParams()
      
      if (filters.riskLevel) {
        params.append('risk_level', filters.riskLevel)
      }
      if (filters.status?.length) {
        params.append('status', filters.status.join(','))
      }
      if (filters.category?.length) {
        params.append('category', filters.category.join(','))
      }
      if (filters.spend) {
        params.append('spend', filters.spend)
      }
      if (filters.contractExpiry) {
        params.append('contract_expiry', filters.contractExpiry)
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

      const response = await api.get(`/vendors/vendors/?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error fetching vendors:', error)
      
      // Return mock data as fallback with Django model structure
      return {
        results: [
          {
            id: 1,
            vendor_id: 'VEN-2024-0001',
            name: 'Microsoft Corporation',
            legal_name: 'Microsoft Corporation',
            category: {
              id: 1,
              name: 'Cloud Services',
              description: 'Cloud computing and software services',
              color_code: '#0078d4',
              risk_weight: 'low',
              compliance_requirements: {}
            },
            business_description: 'Technology corporation providing cloud services and software',
            website: 'https://www.microsoft.com',
            tax_id: '91-1144442',
            duns_number: '796740573',
            address_line1: 'One Microsoft Way',
            address_line2: '',
            city: 'Redmond',
            state_province: 'WA',
            postal_code: '98052',
            country: 'USA',
            status: 'active',
            vendor_type: 'service_provider',
            risk_level: 'low',
            risk_score: 15.5,
            annual_spend: 120000,
            credit_rating: 'AAA',
            payment_terms: 'Net 30',
            operating_regions: ['US', 'EU', 'APAC'],
            primary_region: 'US',
            custom_fields: {},
            certifications: ['ISO 27001', 'SOC 2 Type II'],
            compliance_status: { gdpr: 'compliant', sox: 'compliant' },
            data_processing_agreement: true,
            security_assessment_completed: true,
            security_assessment_date: '2024-03-15',
            assigned_to: {
              id: 1,
              username: 'procurement.manager',
              first_name: 'John',
              last_name: 'Smith',
              email: 'john.smith@company.com'
            },
            relationship_start_date: '2023-06-30',
            created_at: '2023-06-30T10:00:00Z',
            updated_at: '2024-08-20T15:30:00Z',
            created_by: {
              id: 1,
              username: 'admin',
              first_name: 'Admin',
              last_name: 'User'
            }
          },
          {
            id: 2,
            vendor_id: 'VEN-2024-0002',
            name: 'Amazon Web Services',
            legal_name: 'Amazon Web Services, Inc.',
            category: {
              id: 2,
              name: 'Infrastructure',
              description: 'Cloud infrastructure and computing services',
              color_code: '#ff9900',
              risk_weight: 'low',
              compliance_requirements: {}
            },
            business_description: 'Cloud computing platform and web services',
            website: 'https://aws.amazon.com',
            tax_id: '91-1646860',
            duns_number: '962274814',
            address_line1: '410 Terry Ave N',
            address_line2: '',
            city: 'Seattle',
            state_province: 'WA',
            postal_code: '98109',
            country: 'USA',
            status: 'active',
            vendor_type: 'service_provider',
            risk_level: 'low',
            risk_score: 18.2,
            annual_spend: 85000,
            credit_rating: 'AAA',
            payment_terms: 'Net 45',
            operating_regions: ['US', 'EU', 'APAC'],
            primary_region: 'US',
            custom_fields: {},
            certifications: ['ISO 27001', 'SOC 1 Type II', 'SOC 2 Type II'],
            compliance_status: { gdpr: 'compliant', sox: 'compliant' },
            data_processing_agreement: true,
            security_assessment_completed: true,
            security_assessment_date: '2024-02-20',
            assigned_to: {
              id: 2,
              username: 'it.manager',
              first_name: 'Sarah',
              last_name: 'Johnson',
              email: 'sarah.johnson@company.com'
            },
            relationship_start_date: '2023-01-15',
            created_at: '2023-01-15T09:00:00Z',
            updated_at: '2024-08-18T14:20:00Z',
            created_by: {
              id: 2,
              username: 'it.admin',
              first_name: 'IT',
              last_name: 'Admin'
            }
          }
        ],
        count: 2,
        next: null,
        previous: null
      }
    }
  },

  // Get single vendor by ID
  async getVendor(id: string | number): Promise<Vendor> {
    try {
      const response = await api.get(`/vendors/vendors/${id}/`)
      return response.data
    } catch (error) {
      console.error('Error fetching vendor:', error)
      throw error
    }
  },

  // Create new vendor
  async createVendor(vendorData: Partial<Vendor>): Promise<Vendor> {
    try {
      const response = await api.post('/vendors/vendors/', vendorData)
      return response.data
    } catch (error) {
      console.error('Error creating vendor:', error)
      throw error
    }
  },

  // Update vendor
  async updateVendor(id: string | number, vendorData: Partial<Vendor>): Promise<Vendor> {
    try {
      const response = await api.patch(`/vendors/vendors/${id}/`, vendorData)
      return response.data
    } catch (error) {
      console.error('Error updating vendor:', error)
      throw error
    }
  },

  // Delete vendor
  async deleteVendor(id: string | number): Promise<void> {
    try {
      await api.delete(`/vendors/vendors/${id}/`)
    } catch (error) {
      console.error('Error deleting vendor:', error)
      throw error
    }
  },

  // Get vendor analytics
  async getVendorAnalytics() {
    try {
      const response = await api.get('/vendors/analytics/dashboard/')
      return response.data
    } catch (error) {
      console.error('Error fetching vendor analytics:', error)
      
      // Return mock analytics as fallback
      return {
        totalVendors: 89,
        contractsExpiring: 8,
        highRiskVendors: 6,
        avgPerformance: 88.5,
        performanceTrend: 3.2
      }
    }
  },

  // Get vendor categories
  async getVendorCategories(): Promise<VendorCategory[]> {
    try {
      const response = await api.get('/vendors/categories/')
      return response.data.results || response.data
    } catch (error) {
      console.error('Error fetching vendor categories:', error)
      return [
        { id: 1, name: 'Cloud Services', description: 'Cloud computing and software services', color_code: '#0078d4', risk_weight: 'low', compliance_requirements: {} },
        { id: 2, name: 'Infrastructure', description: 'Cloud infrastructure and computing services', color_code: '#ff9900', risk_weight: 'low', compliance_requirements: {} },
        { id: 3, name: 'Software', description: 'Software vendors and applications', color_code: '#00bcf2', risk_weight: 'medium', compliance_requirements: {} }
      ]
    }
  },

  // Get vendor contacts
  async getVendorContacts(vendorId: number): Promise<VendorContact[]> {
    try {
      const response = await api.get(`/vendors/contacts/?vendor=${vendorId}`)
      return response.data.results || response.data
    } catch (error) {
      console.error('Error fetching vendor contacts:', error)
      return []
    }
  },

  // Get vendor choices (status, types, etc.) from Django
  async getVendorChoices(): Promise<{
    status_choices: Array<{value: string, label: string}>,
    vendor_type_choices: Array<{value: string, label: string}>,
    risk_level_choices: Array<{value: string, label: string}>
  }> {
    try {
      const response = await api.get('/vendors/choices/')
      return response.data
    } catch (error) {
      console.error('Error fetching vendor choices:', error)
      return {
        status_choices: [
          { value: 'active', label: 'Active' },
          { value: 'inactive', label: 'Inactive' },
          { value: 'under_review', label: 'Under Review' },
          { value: 'approved', label: 'Approved' },
          { value: 'suspended', label: 'Suspended' },
          { value: 'terminated', label: 'Terminated' }
        ],
        vendor_type_choices: [
          { value: 'supplier', label: 'Supplier' },
          { value: 'service_provider', label: 'Service Provider' },
          { value: 'consultant', label: 'Consultant' },
          { value: 'contractor', label: 'Contractor' },
          { value: 'partner', label: 'Strategic Partner' },
          { value: 'subcontractor', label: 'Subcontractor' }
        ],
        risk_level_choices: [
          { value: 'low', label: 'Low' },
          { value: 'medium', label: 'Medium' },
          { value: 'high', label: 'High' },
          { value: 'critical', label: 'Critical' }
        ]
      }
    }
  }
}

export default vendorService