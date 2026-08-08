import { Typography } from "antd";
import type { ReactNode } from "react";

const { Title, Text } = Typography;

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  icon?: ReactNode;
  actions?: ReactNode;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  icon,
  actions,
}: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header-copy">
        {eyebrow ? <Text className="page-header-eyebrow">{eyebrow}</Text> : null}
        <Title level={2} className="page-header-title">
          {icon ? <span className="page-header-icon" aria-hidden="true">{icon}</span> : null}
          {title}
        </Title>
        {description ? <Text className="page-header-description">{description}</Text> : null}
      </div>
      {actions ? <div className="page-header-actions">{actions}</div> : null}
    </header>
  );
}
