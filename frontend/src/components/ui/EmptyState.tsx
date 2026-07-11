"use client";
import { Empty, Button, Typography, Space } from "antd";
import {
  FileTextOutlined,
  PlusOutlined,
  InboxOutlined,
  SearchOutlined,
  FilterOutlined,
  ExclamationCircleOutlined,
  CheckSquareOutlined,
  SafetyOutlined,
  TeamOutlined,
  VideoCameraOutlined,
  RadarChartOutlined,
  BugOutlined,
  DatabaseOutlined
} from "@ant-design/icons";
import { useTheme } from "@/theme";

interface EmptyStateProps {
  type?: 'default' | 'search' | 'filter' | 'error' | 'maintenance' | 'assessments' | 'risks' | 'vendors' | 'policies' | 'training' | 'vulnerabilities' | 'evidence';
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    text: string;
    onClick: () => void;
    type?: 'primary' | 'default';
    icon?: React.ReactNode;
  };
  secondaryAction?: {
    text: string;
    onClick: () => void;
    icon?: React.ReactNode;
  };
  children?: React.ReactNode;
  image?: string | React.ReactNode;
  size?: 'small' | 'default' | 'large';
}

// Predefined empty state configurations
const EmptyStateConfigs = {
  // Generic states
  default: {
    icon: <InboxOutlined />,
    title: "No data available",
    description: "There are no items to display at the moment."
  },
  search: {
    icon: <SearchOutlined />,
    title: "No search results",
    description: "We couldn't find any items matching your search criteria."
  },
  filter: {
    icon: <FilterOutlined />,
    title: "No filtered results",
    description: "No items match your current filter settings."
  },
  error: {
    icon: <ExclamationCircleOutlined />,
    title: "Something went wrong",
    description: "We're having trouble loading this data. Please try again."
  },
  maintenance: {
    icon: <BugOutlined />,
    title: "Under maintenance",
    description: "This feature is temporarily unavailable while we make improvements."
  },

  // Context-specific states
  assessments: {
    icon: <CheckSquareOutlined />,
    title: "No assessments yet",
    description: "Start by creating your first compliance assessment to track your organization's security posture."
  },
  risks: {
    icon: <SafetyOutlined />,
    title: "No risks identified",
    description: "Your risk register is empty. Add risks to track and manage potential threats."
  },
  vendors: {
    icon: <TeamOutlined />,
    title: "No vendors registered",
    description: "Add your vendors and suppliers to track their compliance and manage relationships."
  },
  policies: {
    icon: <FileTextOutlined />,
    title: "No policies available",
    description: "Create and publish policies to establish your organization's security standards."
  },
  training: {
    icon: <VideoCameraOutlined />,
    title: "No training materials",
    description: "Upload training content to educate your team on security awareness."
  },
  vulnerabilities: {
    icon: <RadarChartOutlined />,
    title: "No vulnerabilities found",
    description: "Run vulnerability scans to identify and track security issues."
  },
  evidence: {
    icon: <DatabaseOutlined />,
    title: "No evidence uploaded",
    description: "Upload documents and files as evidence for your compliance assessments."
  }
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  type = 'default',
  title,
  description,
  icon,
  action,
  secondaryAction,
  children,
  image,
  size = 'default'
}) => {
  const { mode } = useTheme();
  const isDark = mode === 'dark';

  const config = EmptyStateConfigs[type] || EmptyStateConfigs.default;

  const finalTitle = title || config.title;
  const finalDescription = description || config.description;
  const finalIcon = icon || config.icon;

  const containerStyle = {
    padding: size === 'small' ? 24 : size === 'large' ? 48 : 32,
    textAlign: 'center' as const,
    backgroundColor: 'transparent',
  };

  const titleStyle = {
    fontSize: size === 'small' ? 16 : size === 'large' ? 20 : 18,
    fontWeight: 600,
    color: isDark ? '#F8FAFC' : '#0F172A',
    marginBottom: 8,
  };

  const descriptionStyle = {
    fontSize: size === 'small' ? 13 : 14,
    color: isDark ? '#94A3B8' : '#64748B',
    marginBottom: action || secondaryAction ? 24 : 0,
    maxWidth: 400,
    margin: '0 auto',
    lineHeight: 1.6,
  };

  const iconStyle = {
    fontSize: size === 'small' ? 48 : size === 'large' ? 72 : 64,
    color: isDark ? '#475569' : '#CBD5E1',
    marginBottom: 16,
  };

  return (
    <div style={containerStyle}>
      {image ? (
        <div style={{ marginBottom: 24 }}>
          {typeof image === 'string' ? (
            <img
              src={image}
              alt="Empty state"
              style={{
                maxWidth: size === 'small' ? 120 : size === 'large' ? 200 : 160,
                opacity: 0.8
              }}
            />
          ) : (
            image
          )}
        </div>
      ) : (
        <div style={iconStyle}>
          {finalIcon}
        </div>
      )}

      <Typography.Title level={size === 'small' ? 5 : 4} style={titleStyle}>
        {finalTitle}
      </Typography.Title>

      <Typography.Paragraph style={descriptionStyle}>
        {finalDescription}
      </Typography.Paragraph>

      {(action || secondaryAction) && (
        <Space size="middle" wrap>
          {action && (
            <Button
              type={action.type || 'primary'}
              size={size === 'small' ? 'middle' : 'large'}
              icon={action.icon}
              onClick={action.onClick}
              style={{
                borderRadius: 8,
                height: size === 'small' ? 36 : 44,
                paddingInline: size === 'small' ? 16 : 24,
                fontWeight: 600,
              }}
            >
              {action.text}
            </Button>
          )}
          {secondaryAction && (
            <Button
              size={size === 'small' ? 'middle' : 'large'}
              icon={secondaryAction.icon}
              onClick={secondaryAction.onClick}
              style={{
                borderRadius: 8,
                height: size === 'small' ? 36 : 44,
                paddingInline: size === 'small' ? 16 : 24,
              }}
            >
              {secondaryAction.text}
            </Button>
          )}
        </Space>
      )}

      {children && (
        <div style={{ marginTop: 24 }}>
          {children}
        </div>
      )}
    </div>
  );
};

// Convenience components for specific contexts
export const AssessmentsEmptyState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState
    {...props}
    type="assessments"
    action={props.action || {
      text: "Create Assessment",
      icon: <PlusOutlined />,
      onClick: () => console.log("Create assessment clicked")
    }}
  />
);

export const RisksEmptyState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState
    {...props}
    type="risks"
    action={props.action || {
      text: "Add Risk",
      icon: <PlusOutlined />,
      onClick: () => console.log("Add risk clicked")
    }}
  />
);

export const VendorsEmptyState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState
    {...props}
    type="vendors"
    action={props.action || {
      text: "Add Vendor",
      icon: <PlusOutlined />,
      onClick: () => console.log("Add vendor clicked")
    }}
  />
);

export const PoliciesEmptyState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState
    {...props}
    type="policies"
    action={props.action || {
      text: "Create Policy",
      icon: <PlusOutlined />,
      onClick: () => console.log("Create policy clicked")
    }}
  />
);

export const TrainingEmptyState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState
    {...props}
    type="training"
    action={props.action || {
      text: "Upload Content",
      icon: <PlusOutlined />,
      onClick: () => console.log("Upload training clicked")
    }}
  />
);

export const VulnerabilitiesEmptyState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState
    {...props}
    type="vulnerabilities"
    action={props.action || {
      text: "Run Scan",
      icon: <RadarChartOutlined />,
      onClick: () => console.log("Run scan clicked")
    }}
  />
);

export const SearchEmptyState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState
    {...props}
    type="search"
    secondaryAction={props.secondaryAction || {
      text: "Clear Search",
      icon: <SearchOutlined />,
      onClick: () => console.log("Clear search clicked")
    }}
  />
);

export const FilterEmptyState: React.FC<Omit<EmptyStateProps, 'type'>> = (props) => (
  <EmptyState
    {...props}
    type="filter"
    secondaryAction={props.secondaryAction || {
      text: "Clear Filters",
      icon: <FilterOutlined />,
      onClick: () => console.log("Clear filters clicked")
    }}
  />
);