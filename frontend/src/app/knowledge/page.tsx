"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Col,
  Empty,
  Input,
  List,
  Modal,
  Row,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import { BookOutlined, SearchOutlined } from "@ant-design/icons";
import {
  KnowledgeArticle,
  KnowledgeCategory,
  getKnowledgeArticle,
  getKnowledgeArticles,
  getKnowledgeCategories,
} from "@/lib/services/knowledgeService";

const { Title, Text, Paragraph } = Typography;

const moduleOptions = [
  { value: "dashboard", label: "Dashboard" },
  { value: "frameworks", label: "Frameworks" },
  { value: "risk", label: "Risk" },
  { value: "assets", label: "Assets" },
  { value: "vendors", label: "Vendors" },
  { value: "policies", label: "Policies" },
  { value: "training", label: "Training" },
  { value: "analytics", label: "Analytics" },
  { value: "vulnerability_scanning", label: "Vulnerabilities" },
  { value: "exports", label: "Exports" },
  { value: "administration", label: "Administration" },
];

export default function KnowledgePage() {
  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [categories, setCategories] = useState<KnowledgeCategory[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<KnowledgeArticle | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [moduleKey, setModuleKey] = useState<string | undefined>();
  const [category, setCategory] = useState<number | undefined>();
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  const loadCategories = async () => {
    try {
      const data = await getKnowledgeCategories();
      setCategories(data.results);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Failed to load categories");
    }
  };

  const loadArticles = async (requestedPage = page) => {
    setLoading(true);
    try {
      const data = await getKnowledgeArticles({
        search: search || undefined,
        module_key: moduleKey,
        category,
        page: requestedPage,
      });
      setArticles(data.results);
      setTotal(data.count);
      setPage(requestedPage);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Failed to load knowledge articles");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCategories();
    loadArticles(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openArticle = async (article: KnowledgeArticle) => {
    setDetailLoading(true);
    try {
      const data = await getKnowledgeArticle(article.slug);
      setSelectedArticle(data);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Failed to open article");
    } finally {
      setDetailLoading(false);
    }
  };

  const categoryOptions = useMemo(
    () => categories.map(item => ({ value: item.id, label: item.name })),
    [categories],
  );

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <BookOutlined style={{ marginRight: 8 }} />
          Knowledge Base
        </Title>
        <Text type="secondary">Search guidance, process notes and module help.</Text>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} lg={10}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Search articles"
              value={search}
              onChange={event => setSearch(event.target.value)}
              onPressEnter={() => loadArticles(1)}
            />
          </Col>
          <Col xs={24} md={8} lg={5}>
            <Select
              allowClear
              placeholder="Module"
              style={{ width: "100%" }}
              options={moduleOptions}
              value={moduleKey}
              onChange={value => setModuleKey(value)}
            />
          </Col>
          <Col xs={24} md={8} lg={5}>
            <Select
              allowClear
              placeholder="Category"
              style={{ width: "100%" }}
              options={categoryOptions}
              value={category}
              onChange={value => setCategory(value)}
            />
          </Col>
          <Col xs={24} md={8} lg={4}>
            <Button type="primary" block icon={<SearchOutlined />} onClick={() => loadArticles(1)}>
              Search
            </Button>
          </Col>
        </Row>
      </Card>

      <Card>
        <List
          loading={loading}
          dataSource={articles}
          locale={{ emptyText: <Empty description="No knowledge articles found" /> }}
          pagination={{
            current: page,
            pageSize: 20,
            total,
            onChange: requestedPage => loadArticles(requestedPage),
          }}
          renderItem={article => (
            <List.Item
              actions={[
                <Button key="open" type="link" onClick={() => openArticle(article)}>
                  Open
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space wrap>
                    <Typography.Link onClick={() => openArticle(article)}>{article.title}</Typography.Link>
                    {article.content_scope === "global" ? <Tag>Global</Tag> : null}
                  </Space>
                }
                description={
                  <Space direction="vertical" size={6}>
                    <Text type="secondary">{article.summary || "No summary provided"}</Text>
                    <Space wrap>
                      {article.category_name ? <Tag color="blue">{article.category_name}</Tag> : null}
                      {article.module_key ? <Tag>{article.module_key.replaceAll("_", " ")}</Tag> : null}
                      {article.workflow_key ? <Tag color="purple">{article.workflow_key}</Tag> : null}
                      {article.tags?.slice(0, 4).map(tag => <Tag key={tag}>{tag}</Tag>)}
                    </Space>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>

      <Modal
        open={Boolean(selectedArticle)}
        title={selectedArticle?.title}
        onCancel={() => setSelectedArticle(null)}
        footer={<Button onClick={() => setSelectedArticle(null)}>Close</Button>}
        width={860}
        confirmLoading={detailLoading}
      >
        {selectedArticle ? (
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Space wrap>
              {selectedArticle.category_name ? <Tag color="blue">{selectedArticle.category_name}</Tag> : null}
              {selectedArticle.module_key ? <Tag>{selectedArticle.module_key.replaceAll("_", " ")}</Tag> : null}
              {selectedArticle.workflow_key ? <Tag color="purple">{selectedArticle.workflow_key}</Tag> : null}
            </Space>
            {selectedArticle.summary ? <Paragraph type="secondary">{selectedArticle.summary}</Paragraph> : null}
            <Paragraph style={{ whiteSpace: "pre-wrap" }}>{selectedArticle.body}</Paragraph>
          </Space>
        ) : null}
      </Modal>
    </div>
  );
}
