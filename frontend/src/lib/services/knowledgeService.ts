import api from "@/lib/api";
import { PaginatedResponse } from "@/lib/services/assetService";

export interface KnowledgeCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  module_key: string;
  sort_order: number;
  is_active: boolean;
  article_count?: number;
}

export interface KnowledgeArticle {
  id: number;
  title: string;
  slug: string;
  summary: string;
  body?: string;
  category?: number | null;
  category_name?: string;
  module_key: string;
  workflow_key: string;
  tags: string[];
  status: string;
  content_scope: string;
  published_at?: string | null;
  updated_at?: string;
}

export async function getKnowledgeCategories(params: { module_key?: string; search?: string } = {}) {
  const { data } = await api.get<PaginatedResponse<KnowledgeCategory>>("/knowledge/categories/", { params });
  return data;
}

export async function getKnowledgeArticles(params: {
  search?: string;
  module_key?: string;
  category?: number;
  page?: number;
} = {}) {
  const { data } = await api.get<PaginatedResponse<KnowledgeArticle>>("/knowledge/articles/", { params });
  return data;
}

export async function getKnowledgeArticle(slug: string) {
  const { data } = await api.get<KnowledgeArticle>(`/knowledge/articles/${slug}/`);
  return data;
}

export async function getContextualKnowledge(params: { module_key: string; workflow_key?: string }) {
  const { data } = await api.get<{ results: KnowledgeArticle[] }>("/knowledge/articles/contextual/", { params });
  return data;
}
