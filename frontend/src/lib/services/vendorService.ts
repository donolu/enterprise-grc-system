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

export interface VendorAnalytics {
  totalVendors: number
  contractsExpiring: number
  highRiskVendors: number
  avgPerformance: number
}

interface VendorSummaryResponse {
  total_vendors: number
  contracts_expiring_soon: number
  high_risk_vendors: number
  average_performance_score: number | string | null
}

export interface VendorChoices {
  status_choices: Array<{ value: string; label: string }>
  vendor_type_choices: Array<{ value: string; label: string }>
  risk_level_choices: Array<{ value: string; label: string }>
}

export const vendorService = {
  // Get all vendors with optional filtering
  async getVendors(filters: VendorFilters = {}): Promise<PaginatedResponse<Vendor>> {
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
  },

  // Get single vendor by ID
  async getVendor(id: string | number): Promise<Vendor> {
    const response = await api.get(`/vendors/vendors/${id}/`)
    return response.data
  },

  // Create new vendor
  async createVendor(vendorData: Partial<Vendor>): Promise<Vendor> {
    const response = await api.post('/vendors/vendors/', vendorData)
    return response.data
  },

  // Update vendor
  async updateVendor(id: string | number, vendorData: Partial<Vendor>): Promise<Vendor> {
    const response = await api.patch(`/vendors/vendors/${id}/`, vendorData)
    return response.data
  },

  // Delete vendor
  async deleteVendor(id: string | number): Promise<void> {
    await api.delete(`/vendors/vendors/${id}/`)
  },

  async getVendorAnalytics(): Promise<VendorAnalytics> {
    const response = await api.get<VendorSummaryResponse>('/vendors/vendors/summary/')
    return {
      totalVendors: response.data.total_vendors,
      contractsExpiring: response.data.contracts_expiring_soon,
      highRiskVendors: response.data.high_risk_vendors,
      avgPerformance: Number(response.data.average_performance_score ?? 0),
    }
  },

  async getVendorCategories(): Promise<VendorCategory[]> {
    const response = await api.get('/vendors/categories/')
    return response.data.results || response.data
  },

  // Get vendor contacts
  async getVendorContacts(vendorId: number): Promise<VendorContact[]> {
    const response = await api.get(`/vendors/contacts/?vendor=${vendorId}`)
    return response.data.results || response.data
  },

  async getVendorChoices(): Promise<VendorChoices> {
    const response = await api.get<VendorChoices>('/vendors/vendors/choices/')
    return response.data
  }
}

export default vendorService
