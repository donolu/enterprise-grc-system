"use client";
import { Tag, Badge } from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  MinusCircleOutlined,
  SyncOutlined,
  WarningOutlined,
  StopOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined
} from "@ant-design/icons";
import { useTheme } from "@/theme";

// Status definitions for different contexts
export const StatusConfigs = {
  // Assessment statuses
  assessment: {
    'not-started': {
      color: 'default',
      icon: <MinusCircleOutlined />,
      label: 'Not Started'
    },
    'pending': {
      color: 'processing',
      icon: <ClockCircleOutlined />,
      label: 'Pending'
    },
    'in-progress': {
      color: 'processing',
      icon: <SyncOutlined spin />,
      label: 'In Progress'
    },
    'under-review': {
      color: 'warning',
      icon: <ExclamationCircleOutlined />,
      label: 'Under Review'
    },
    'complete': {
      color: 'success',
      icon: <CheckCircleOutlined />,
      label: 'Complete'
    },
    'overdue': {
      color: 'error',
      icon: <WarningOutlined />,
      label: 'Overdue'
    }
  },

  // Risk statuses
  risk: {
    'identified': {
      color: 'warning',
      icon: <ExclamationCircleOutlined />,
      label: 'Identified'
    },
    'assessed': {
      color: 'processing',
      icon: <ClockCircleOutlined />,
      label: 'Assessed'
    },
    'mitigating': {
      color: 'processing',
      icon: <SyncOutlined spin />,
      label: 'Mitigating'
    },
    'mitigated': {
      color: 'success',
      icon: <CheckCircleOutlined />,
      label: 'Mitigated'
    },
    'accepted': {
      color: 'default',
      icon: <CheckCircleOutlined />,
      label: 'Accepted'
    },
    'closed': {
      color: 'success',
      icon: <CheckCircleOutlined />,
      label: 'Closed'
    }
  },

  // Priority levels
  priority: {
    'low': {
      color: 'success',
      icon: <MinusCircleOutlined />,
      label: 'Low'
    },
    'medium': {
      color: 'warning',
      icon: <ExclamationCircleOutlined />,
      label: 'Medium'
    },
    'high': {
      color: 'error',
      icon: <WarningOutlined />,
      label: 'High'
    },
    'critical': {
      color: 'error',
      icon: <WarningOutlined />,
      label: 'Critical'
    }
  },

  // Compliance levels
  compliance: {
    'compliant': {
      color: 'success',
      icon: <CheckCircleOutlined />,
      label: 'Compliant'
    },
    'partially-compliant': {
      color: 'warning',
      icon: <ExclamationCircleOutlined />,
      label: 'Partially Compliant'
    },
    'non-compliant': {
      color: 'error',
      icon: <StopOutlined />,
      label: 'Non-Compliant'
    },
    'not-assessed': {
      color: 'default',
      icon: <MinusCircleOutlined />,
      label: 'Not Assessed'
    }
  },

  // Policy statuses
  policy: {
    'draft': {
      color: 'default',
      icon: <MinusCircleOutlined />,
      label: 'Draft'
    },
    'review': {
      color: 'processing',
      icon: <ClockCircleOutlined />,
      label: 'Under Review'
    },
    'approved': {
      color: 'success',
      icon: <CheckCircleOutlined />,
      label: 'Approved'
    },
    'published': {
      color: 'success',
      icon: <PlayCircleOutlined />,
      label: 'Published'
    },
    'archived': {
      color: 'default',
      icon: <PauseCircleOutlined />,
      label: 'Archived'
    },
    'expired': {
      color: 'error',
      icon: <StopOutlined />,
      label: 'Expired'
    }
  },

  // Vendor statuses
  vendor: {
    'active': {
      color: 'success',
      icon: <CheckCircleOutlined />,
      label: 'Active'
    },
    'pending': {
      color: 'processing',
      icon: <ClockCircleOutlined />,
      label: 'Pending'
    },
    'suspended': {
      color: 'warning',
      icon: <PauseCircleOutlined />,
      label: 'Suspended'
    },
    'terminated': {
      color: 'error',
      icon: <StopOutlined />,
      label: 'Terminated'
    }
  }
};

interface StatusTagProps {
  status: string;
  context: keyof typeof StatusConfigs;
  size?: 'small' | 'default' | 'large';
  showIcon?: boolean;
  bordered?: boolean;
  style?: React.CSSProperties;
  onClick?: () => void;
}

export const StatusTag: React.FC<StatusTagProps> = ({
  status,
  context,
  size = 'default',
  showIcon = true,
  bordered = true,
  style,
  onClick
}) => {
  const { mode } = useTheme();
  const isDark = mode === 'dark';

  const config = StatusConfigs[context]?.[status];

  if (!config) {
    return (
      <Tag
        color="default"
        style={{ ...style, textTransform: 'capitalize' }}
        onClick={onClick}
      >
        {status.replace(/[-_]/g, ' ')}
      </Tag>
    );
  }

  const tagStyle = {
    borderRadius: 20,
    paddingInline: size === 'small' ? 8 : size === 'large' ? 16 : 12,
    paddingBlock: size === 'small' ? 2 : size === 'large' ? 6 : 4,
    border: bordered ? undefined : 'none',
    fontWeight: 500,
    fontSize: size === 'small' ? 11 : size === 'large' ? 14 : 12,
    cursor: onClick ? 'pointer' : 'default',
    ...style
  };

  return (
    <Tag
      color={config.color}
      icon={showIcon ? config.icon : undefined}
      style={tagStyle}
      onClick={onClick}
    >
      {config.label}
    </Tag>
  );
};

// Convenience components for specific contexts
export const AssessmentStatusTag: React.FC<Omit<StatusTagProps, 'context'>> = (props) => (
  <StatusTag {...props} context="assessment" />
);

export const RiskStatusTag: React.FC<Omit<StatusTagProps, 'context'>> = (props) => (
  <StatusTag {...props} context="risk" />
);

export const ComplianceStatusTag: React.FC<Omit<StatusTagProps, 'context'>> = (props) => (
  <StatusTag {...props} context="compliance" />
);

export const PolicyStatusTag: React.FC<Omit<StatusTagProps, 'context'>> = (props) => (
  <StatusTag {...props} context="policy" />
);

export const VendorStatusTag: React.FC<Omit<StatusTagProps, 'context'>> = (props) => (
  <StatusTag {...props} context="vendor" />
);

// Status badge component for showing counts
interface StatusBadgeProps {
  status: string;
  context: keyof typeof StatusConfigs;
  count: number;
  size?: 'small' | 'default';
  showZero?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  context,
  count,
  size = 'default',
  showZero = false
}) => {
  const config = StatusConfigs[context]?.[status];

  if (!config) return null;

  return (
    <Badge
      count={count}
      showZero={showZero}
      size={size}
      style={{
        backgroundColor: config.color === 'success' ? '#0EB57D' :
                         config.color === 'error' ? '#E5484D' :
                         config.color === 'warning' ? '#FFB020' :
                         config.color === 'processing' ? '#2F6FED' : '#64748B'
      }}
    >
      <StatusTag status={status} context={context} size={size} />
    </Badge>
  );
};