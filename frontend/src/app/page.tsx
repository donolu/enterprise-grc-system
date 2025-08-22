"use client";
import { Card, Col, Row, Statistic, Tag } from "antd";

export default function Dashboard() {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} md={8} lg={6}>
        <Card>
          <Statistic title="Controls Completed" value={128} suffix="/ 420" />
          <Tag color="success" style={{ marginTop: 8 }}>+12 this week</Tag>
        </Card>
      </Col>
      <Col xs={24} sm={12} md={8} lg={6}>
        <Card>
          <Statistic title="Overdue Tasks" value={7} />
          <Tag color="error" style={{ marginTop: 8 }}>Needs attention</Tag>
        </Card>
      </Col>
      <Col xs={24} sm={12} md={8} lg={6}>
        <Card>
          <Statistic title="Acknowledgment Rate" value={86} suffix="%" />
          <Tag style={{ marginTop: 8 }}>Target 95%</Tag>
        </Card>
      </Col>
    </Row>
  );
}
