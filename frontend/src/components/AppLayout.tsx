"use client";
import { Layout, Menu, Avatar, Typography, Dropdown, Space, Input } from "antd";
import { HomeOutlined, CheckSquareOutlined, SafetyOutlined, TeamOutlined, FileTextOutlined, VideoCameraOutlined, RadarChartOutlined, SettingOutlined } from "@ant-design/icons";
import Link from "next/link";

const { Header, Sider, Content } = Layout;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const items = [
    { key: "dash", icon: <HomeOutlined/>, label: <Link href="/">Dashboard</Link> },
    { key: "assessments", icon: <CheckSquareOutlined/>, label: <Link href="/assessments">Assessments</Link> },
    { key: "risk", icon: <SafetyOutlined/>, label: <Link href="/risk">Risk</Link> },
    { key: "vendors", icon: <TeamOutlined/>, label: <Link href="/vendors">Vendors</Link> },
    { key: "policies", icon: <FileTextOutlined/>, label: <Link href="/policies">Policies</Link> },
    { key: "training", icon: <VideoCameraOutlined/>, label: <Link href="/training">Training</Link> },
    { key: "scans", icon: <RadarChartOutlined/>, label: <Link href="/scans">Vulnerabilities</Link> },
    { key: "admin", icon: <SettingOutlined/>, label: <Link href="/admin">Admin</Link> },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={232} breakpoint="lg" collapsedWidth="0">
        <div style={{ height: 64, display: "flex", alignItems: "center", padding: "0 16px", color: "#fff", fontWeight: 700 }}>
          GRC<span style={{ opacity: .7 }}>Suite</span>
        </div>
        <Menu theme="dark" mode="inline" items={items} />
      </Sider>
      <Layout>
        <Header style={{ display: "flex", alignItems: "center", gap: 12, padding: "0 20px", background: '#fff' }}>
          <Input.Search placeholder="Search controls, vendors, risks…" style={{ maxWidth: 520 }} />
          <div style={{ marginLeft: "auto" }}>
            <Space size={16}>
              <Dropdown menu={{ items: [{key:"tenant",label:"Switch tenant (soon)"}] }}>
                <a>Acme Corp ▾</a>
              </Dropdown>
              <Avatar>AC</Avatar>
            </Space>
          </div>
        </Header>
        <Content style={{ padding: 24 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
