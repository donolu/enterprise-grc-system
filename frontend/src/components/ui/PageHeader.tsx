"use client";

import type { ReactNode } from "react";
import { Typography } from "antd";

const { Title, Text } = Typography;

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  icon?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, icon, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header-copy">
        {eyebrow && <span className="page-header-eyebrow">{eyebrow}</span>}
        <Title level={1} className="page-header-title">
          {icon && <span className="page-header-icon" aria-hidden="true">{icon}</span>}
          {title}
        </Title>
        {description && <Text className="page-header-description">{description}</Text>}
      </div>
      {actions && <div className="page-header-actions">{actions}</div>}
    </header>
  );
}
