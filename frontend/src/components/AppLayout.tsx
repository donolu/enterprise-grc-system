"use client";
import { useEffect, useMemo, useState } from "react";
import { Layout, Menu, Avatar, Typography, Dropdown, Space, Switch, message } from "antd";
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
  DatabaseOutlined,
  QuestionCircleOutlined
} from "@ant-design/icons";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "@/theme";
import { SearchBar } from "@/components/ui";
import { getCurrentSubscription } from "@/lib/services/billingService";
import { checkSession, logout } from "@/lib/auth";

const { Header, Sider, Content } = Layout;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { mode, toggleMode } = useTheme();
  const router = useRouter();
  const [enabledModules, setEnabledModules] = useState<string[] | null>(null);
  const [user, setUser] = useState<{ first_name?: string; last_name?: string; email?: string } | null>(null);

  useEffect(() => {
    let mounted = true;
    getCurrentSubscription()
      .then(subscription => {
        if (mounted) setEnabledModules(subscription.enabled_module_keys);
      })
      .catch(() => {
        if (mounted) setEnabledModules(null);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    checkSession()
      .then((session) => {
        if (mounted) setUser(session);
      })
      .catch(() => {
        if (mounted) setUser(null);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleSignOut = async () => {
    try {
      await logout();
      router.replace("/login");
      router.refresh();
    } catch {
      message.error("We could not end this session. Please try again.");
    }
  };

  const menuItems = useMemo(() => {
    const allItems = [
      { key: "dash", icon: <HomeOutlined/>, label: <Link href="/">Dashboard</Link> },
      { key: "assessments", module: "frameworks", icon: <CheckSquareOutlined/>, label: <Link href="/assessments">Assessments</Link> },
      { key: "risk", module: "risk", icon: <SafetyOutlined/>, label: <Link href="/risk">Risk</Link> },
      { key: "assets", module: "assets", icon: <DatabaseOutlined/>, label: <Link href="/assets">Assets</Link> },
      { key: "vendors", module: "vendors", icon: <TeamOutlined/>, label: <Link href="/vendors">Vendors</Link> },
      { key: "policies", module: "policies", icon: <FileTextOutlined/>, label: <Link href="/policies">Policies</Link> },
      { key: "training", module: "training", icon: <VideoCameraOutlined/>, label: <Link href="/training">Training</Link> },
      { key: "knowledge", icon: <QuestionCircleOutlined/>, label: <Link href="/knowledge">Knowledge</Link> },
      { key: "analytics", module: "analytics", icon: <BarChartOutlined/>, label: <Link href="/analytics">Analytics</Link> },
      { key: "scans", module: "vulnerability_scanning", icon: <RadarChartOutlined/>, label: <Link href="/scans">Vulnerabilities</Link> },
      { key: "admin", icon: <SettingOutlined/>, label: <Link href="/admin">Admin</Link> },
    ];
    if (!enabledModules) return allItems;
    return allItems.filter(item => !item.module || enabledModules.includes(item.module));
  }, [enabledModules]);

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: <Link href="/account/profile">Profile settings</Link>,
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
      onClick: () => void handleSignOut(),
    },
  ];

  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email || "Account";
  const initials = displayName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        width={256}
        breakpoint="lg"
        collapsedWidth="0"
        style={{
          background: mode === 'dark' ? '#0F1419' : '#0F1219',
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
            placeholder="Search risks, vendors and training..."
            style={{ maxWidth: 440 }}
            size="large"
          />

          <div style={{ marginLeft: "auto" }}>
            <Space size={20}>
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
                  {initials || <UserOutlined />}
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
