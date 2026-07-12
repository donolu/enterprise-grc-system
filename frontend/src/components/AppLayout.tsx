"use client";
import { Layout, Menu, Avatar, Typography, Dropdown, Space, Switch, Badge } from "antd";
import {
  HomeOutlined,
  CheckSquareOutlined,
  SafetyOutlined,
  TeamOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
  RadarChartOutlined,
  BarChartOutlined,
  SettingOutlined,
  BulbOutlined,
  BulbFilled,
  UserOutlined,
  LogoutOutlined,
  BellOutlined
} from "@ant-design/icons";
import Link from "next/link";
import { useTheme } from "@/theme";
import { SearchBar } from "@/components/ui";

const { Header, Sider, Content } = Layout;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { mode, toggleMode } = useTheme();

  const menuItems = [
    { key: "dash", icon: <HomeOutlined/>, label: <Link href="/">Dashboard</Link> },
    { key: "assessments", icon: <CheckSquareOutlined/>, label: <Link href="/assessments">Assessments</Link> },
    { key: "risk", icon: <SafetyOutlined/>, label: <Link href="/risk">Risk</Link> },
    { key: "vendors", icon: <TeamOutlined/>, label: <Link href="/vendors">Vendors</Link> },
    { key: "policies", icon: <FileTextOutlined/>, label: <Link href="/policies">Policies</Link> },
    { key: "training", icon: <VideoCameraOutlined/>, label: <Link href="/training">Training</Link> },
    { key: "analytics", icon: <BarChartOutlined/>, label: <Link href="/analytics">Analytics</Link> },
    { key: "scans", icon: <RadarChartOutlined/>, label: <Link href="/scans">Vulnerabilities</Link> },
    { key: "admin", icon: <SettingOutlined/>, label: <Link href="/admin">Admin</Link> },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile Settings',
    },
    {
      key: 'theme',
      icon: mode === 'dark' ? <BulbFilled /> : <BulbOutlined />,
      label: (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
          <span>{mode === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
          <Switch

            checked={mode === 'dark'}
            onChange={toggleMode}
            checkedChildren={<BulbFilled />}
            unCheckedChildren={<BulbOutlined />}
          />
        </div>
      ),
      onClick: (e: { domEvent: { preventDefault: () => void } }) => {
        e.domEvent.preventDefault();
        toggleMode();
      }
    },
    { key: 'div1', type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Sign Out',
      danger: true,
    },
  ];

  const tenantMenuItems = [
    { key: "tenant", label: "Switch Tenant", disabled: true },
    { key: 'div2', type: 'divider' as const },
    { key: "acme", label: "Acme Corp" },
    { key: "demo", label: "Demo Company", disabled: true },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={256}
        breakpoint="lg"
        collapsedWidth="0"
        style={{
          boxShadow: mode === 'dark'
            ? '2px 0 8px rgba(0,0,0,0.3)'
            : '2px 0 8px rgba(0,0,0,0.06)'
        }}
      >
        <div style={{
          height: 64,
          display: "flex",
          alignItems: "center",
          padding: "0 20px",
          borderBottom: `1px solid ${mode === 'dark' ? '#2A3441' : '#E7EBF0'}`,
          marginBottom: 8
        }}>
          <Typography.Title
            level={4}
            style={{
              color: mode === 'dark' ? '#F8FAFC' : '#FFFFFF',
              margin: 0,
              fontWeight: 700,
              letterSpacing: '-0.5px'
            }}
          >
            GRC<span style={{ opacity: 0.7, fontWeight: 400 }}>Suite</span>
          </Typography.Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          items={menuItems}
          style={{
            borderRight: 0,
            fontSize: 14,
          }}
        />
      </Sider>
      <Layout>
        <Header style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          padding: "0 24px",
          borderBottom: `1px solid ${mode === 'dark' ? '#2A3441' : '#E7EBF0'}`,
          boxShadow: mode === 'dark'
            ? '0 2px 8px rgba(0,0,0,0.3)'
            : '0 2px 8px rgba(0,0,0,0.06)'
        }}>
          <SearchBar
            placeholder="Search controls, vendors, risks, policies..."
            style={{ maxWidth: 440 }}
            size="large"
          />

          <div style={{ marginLeft: "auto" }}>
            <Space size={20}>
              <Badge count={3}>
                <BellOutlined style={{
                  fontSize: 18,
                  color: mode === 'dark' ? '#CBD5E1' : '#64748B',
                  cursor: 'pointer'
                }} />
              </Badge>

              <Dropdown
                menu={{ items: tenantMenuItems }}
                placement="bottomRight"
                trigger={['click']}
              >
                <a style={{
                  color: mode === 'dark' ? '#F8FAFC' : '#0F172A',
                  fontWeight: 500,
                  textDecoration: 'none'
                }}>
                  Acme Corp ▾
                </a>
              </Dropdown>

              <Dropdown
                menu={{ items: userMenuItems }}
                placement="bottomRight"
                trigger={['click']}
              >
                <Avatar
                  style={{
                    backgroundColor: '#2F6FED',
                    cursor: 'pointer',
                    border: `2px solid ${mode === 'dark' ? '#2A3441' : '#E7EBF0'}`
                  }}
                  size={36}
                >
                  AC
                </Avatar>
              </Dropdown>
            </Space>
          </div>
        </Header>
        <Content style={{
          padding: 32,
          minHeight: 'calc(100vh - 64px)',
          overflow: 'auto'
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
