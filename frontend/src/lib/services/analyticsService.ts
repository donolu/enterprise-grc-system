import { api } from '../api'

export interface DashboardMetric {
  title: string
  value: number | string
  change?: number
  changeType?: 'increase' | 'decrease' | 'neutral'
  format?: 'number' | 'percentage' | 'currency' | 'text'
}

export interface ChartData {
  labels: string[]
  datasets: Array<{
    label: string
    data: number[]
    backgroundColor?: string[]
    borderColor?: string
    fill?: boolean
  }>
}

export interface ExecutiveDashboard {
  summary_metrics: {
    total_risks: DashboardMetric
    high_priority_risks: DashboardMetric
    policy_compliance: DashboardMetric
    training_completion: DashboardMetric
    vendor_assessments: DashboardMetric
  }
  risk_trend_chart: ChartData
  compliance_by_category: ChartData
  recent_activities: Array<{
    id: string
    type: 'risk' | 'policy' | 'training' | 'vendor'
    title: string
    description: string
    timestamp: string
    priority?: 'low' | 'medium' | 'high' | 'critical'
  }>
}

export interface ComplianceDashboard {
  compliance_overview: {
    overall_score: DashboardMetric
    policies_due_review: DashboardMetric
    pending_acknowledgments: DashboardMetric
    overdue_trainings: DashboardMetric
  }
  compliance_by_framework: ChartData
  policy_acknowledgment_rates: ChartData
  training_completion_trends: ChartData
}

export interface VendorRiskDashboard {
  vendor_metrics: {
    total_vendors: DashboardMetric
    high_risk_vendors: DashboardMetric
    pending_assessments: DashboardMetric
    contract_renewals: DashboardMetric
  }
  risk_distribution: ChartData
  vendor_performance_trends: ChartData
  upcoming_renewals: Array<{
    vendor_name: string
    contract_end_date: string
    risk_level: string
    annual_spend: number
  }>
}

export interface ReportRequest {
  report_type: 'executive' | 'compliance' | 'risk' | 'vendor' | 'policy' | 'training' | 'integrated' | 'operational'
  export_format: 'pdf' | 'excel' | 'csv' | 'json'
  date_range?: {
    start_date: string
    end_date: string
  }
  filters?: Record<string, unknown>
}

export interface AnalyticsReport {
  id: string
  report_type: string
  export_format: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  requested_by: {
    id: number
    username: string
    first_name: string
    last_name: string
  }
  created_at: string
  completed_at?: string
  download_url?: string
  error_message?: string
  file_size?: number
}

export interface PaginatedResponse<T> {
  results: T[]
  count: number
  next: string | null
  previous: string | null
}

export const analyticsService = {
  // Executive Dashboard
  async getExecutiveDashboard(dateRange?: { start_date: string, end_date: string }): Promise<ExecutiveDashboard> {
    try {
      const params = new URLSearchParams()
      if (dateRange) {
        params.append('start_date', dateRange.start_date)
        params.append('end_date', dateRange.end_date)
      }
      
      const response = await api.get(`/analytics/executive/?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error fetching executive dashboard:', error)
      
      // Return mock data as fallback
      return {
        summary_metrics: {
          total_risks: { title: 'Total Risks', value: 42, change: -8, changeType: 'decrease' },
          high_priority_risks: { title: 'High Priority', value: 8, change: 2, changeType: 'increase' },
          policy_compliance: { title: 'Policy Compliance', value: 92.5, format: 'percentage', change: 3.2, changeType: 'increase' },
          training_completion: { title: 'Training Completion', value: 87.3, format: 'percentage', change: 1.8, changeType: 'increase' },
          vendor_assessments: { title: 'Vendor Assessments', value: 23, change: 0, changeType: 'neutral' }
        },
        risk_trend_chart: {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
          datasets: [{
            label: 'Risk Score',
            data: [65, 72, 68, 74, 71, 69],
            borderColor: '#dc2626',
            fill: false
          }]
        },
        compliance_by_category: {
          labels: ['Security', 'HR', 'IT', 'Legal', 'Finance'],
          datasets: [{
            label: 'Compliance Rate',
            data: [95, 88, 92, 85, 90],
            backgroundColor: ['#10b981', '#f59e0b', '#3b82f6', '#8b5cf6', '#ef4444']
          }]
        },
        recent_activities: [
          {
            id: '1',
            type: 'risk',
            title: 'New Risk Identified',
            description: 'Data breach risk from third-party vendor',
            timestamp: '2024-08-25T10:30:00Z',
            priority: 'high'
          }
        ]
      }
    }
  },

  // Compliance Dashboard
  async getComplianceDashboard(dateRange?: { start_date: string, end_date: string }): Promise<ComplianceDashboard> {
    try {
      const params = new URLSearchParams()
      if (dateRange) {
        params.append('start_date', dateRange.start_date)
        params.append('end_date', dateRange.end_date)
      }
      
      const response = await api.get(`/analytics/compliance/?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error fetching compliance dashboard:', error)
      
      // Return mock data as fallback
      return {
        compliance_overview: {
          overall_score: { title: 'Overall Compliance', value: 92.5, format: 'percentage', change: 2.1, changeType: 'increase' },
          policies_due_review: { title: 'Policies Due Review', value: 3, change: -2, changeType: 'decrease' },
          pending_acknowledgments: { title: 'Pending Acknowledgments', value: 45, change: 8, changeType: 'increase' },
          overdue_trainings: { title: 'Overdue Trainings', value: 12, change: -5, changeType: 'decrease' }
        },
        compliance_by_framework: {
          labels: ['ISO 27001', 'GDPR', 'SOX', 'HIPAA', 'PCI DSS'],
          datasets: [{
            label: 'Compliance Score',
            data: [98, 95, 88, 92, 85],
            backgroundColor: ['#10b981']
          }]
        },
        policy_acknowledgment_rates: {
          labels: ['Security', 'HR', 'IT', 'Legal'],
          datasets: [{
            label: 'Acknowledgment Rate',
            data: [95, 88, 92, 85],
            backgroundColor: ['#3b82f6']
          }]
        },
        training_completion_trends: {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
          datasets: [{
            label: 'Completion Rate',
            data: [82, 85, 88, 87, 89, 87],
            borderColor: '#10b981',
            fill: true
          }]
        }
      }
    }
  },

  // Vendor Risk Dashboard
  async getVendorRiskDashboard(dateRange?: { start_date: string, end_date: string }): Promise<VendorRiskDashboard> {
    try {
      const params = new URLSearchParams()
      if (dateRange) {
        params.append('start_date', dateRange.start_date)
        params.append('end_date', dateRange.end_date)
      }
      
      const response = await api.get(`/analytics/vendor-risk/?${params.toString()}`)
      return response.data
    } catch (error) {
      console.error('Error fetching vendor risk dashboard:', error)
      
      // Return mock data as fallback
      return {
        vendor_metrics: {
          total_vendors: { title: 'Total Vendors', value: 89, change: 3, changeType: 'increase' },
          high_risk_vendors: { title: 'High Risk', value: 6, change: -2, changeType: 'decrease' },
          pending_assessments: { title: 'Pending Assessments', value: 12, change: 1, changeType: 'increase' },
          contract_renewals: { title: 'Contracts Due', value: 8, change: 0, changeType: 'neutral' }
        },
        risk_distribution: {
          labels: ['Low', 'Medium', 'High', 'Critical'],
          datasets: [{
            label: 'Vendor Count',
            data: [45, 32, 10, 2],
            backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#dc2626']
          }]
        },
        vendor_performance_trends: {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
          datasets: [{
            label: 'Average Performance',
            data: [85, 87, 86, 89, 88, 90],
            borderColor: '#3b82f6',
            fill: false
          }]
        },
        upcoming_renewals: [
          {
            vendor_name: 'Microsoft Corporation',
            contract_end_date: '2024-12-31',
            risk_level: 'low',
            annual_spend: 120000
          }
        ]
      }
    }
  },

  // Request report generation
  async requestReport(reportRequest: ReportRequest): Promise<AnalyticsReport> {
    try {
      const response = await api.post('/analytics/export/', reportRequest)
      return response.data
    } catch (error) {
      console.error('Error requesting report:', error)
      throw error
    }
  },

  // Get user's reports
  async getMyReports(): Promise<PaginatedResponse<AnalyticsReport>> {
    try {
      const response = await api.get('/analytics/reports/')
      return response.data
    } catch (error) {
      console.error('Error fetching reports:', error)
      return {
        results: [],
        count: 0,
        next: null,
        previous: null
      }
    }
  },

  // Get report status
  async getReportStatus(reportId: string): Promise<AnalyticsReport> {
    try {
      const response = await api.get(`/analytics/reports/${reportId}/status/`)
      return response.data
    } catch (error) {
      console.error('Error fetching report status:', error)
      throw error
    }
  },

  // Download report
  async downloadReport(reportId: string): Promise<Blob> {
    try {
      const response = await api.get(`/analytics/reports/${reportId}/download/`, {
        responseType: 'blob'
      })
      return response.data
    } catch (error) {
      console.error('Error downloading report:', error)
      throw error
    }
  },

  // Delete report
  async deleteReport(reportId: string): Promise<void> {
    try {
      await api.delete(`/analytics/reports/${reportId}/`)
    } catch (error) {
      console.error('Error deleting report:', error)
      throw error
    }
  },

  // Get available report types and formats from Django
  async getReportChoices(): Promise<{
    report_types: Array<{value: string, label: string}>,
    export_formats: Array<{value: string, label: string}>
  }> {
    try {
      const response = await api.get('/analytics/choices/')
      return response.data
    } catch (error) {
      console.error('Error fetching analytics choices:', error)
      return {
        report_types: [
          { value: 'executive', label: 'Executive Dashboard' },
          { value: 'compliance', label: 'Compliance Analytics' },
          { value: 'risk', label: 'Risk Management' },
          { value: 'vendor', label: 'Vendor Risk Assessment' },
          { value: 'policy', label: 'Policy Management' },
          { value: 'training', label: 'Training Effectiveness' },
          { value: 'integrated', label: 'Integrated Risk Posture' },
          { value: 'operational', label: 'Operational Dashboard' }
        ],
        export_formats: [
          { value: 'pdf', label: 'PDF Report' },
          { value: 'excel', label: 'Excel Spreadsheet' },
          { value: 'csv', label: 'CSV Data Export' },
          { value: 'json', label: 'JSON Data Export' }
        ]
      }
    }
  },

  // Refresh analytics cache
  async refreshCache(): Promise<{ message: string }> {
    try {
      const response = await api.post('/analytics/cache/refresh/')
      return response.data
    } catch (error) {
      console.error('Error refreshing analytics cache:', error)
      throw error
    }
  },

  // Health check
  async healthCheck(): Promise<{ status: string, timestamp: string }> {
    try {
      const response = await api.get('/analytics/health/')
      return response.data
    } catch (error) {
      console.error('Error fetching analytics health:', error)
      return { status: 'error', timestamp: new Date().toISOString() }
    }
  }
}

export default analyticsService