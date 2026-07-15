import api from "@/lib/api";

export interface Asset {
  id: number;
  asset_id: string;
  name: string;
  asset_type: string;
  description?: string;
  classification: string;
  criticality: string;
  lifecycle_status: string;
  owner?: number | null;
  owner_display?: string;
  owner_name?: string;
  location?: string;
  next_review_date?: string | null;
  is_review_overdue?: boolean;
  days_until_review?: number | null;
}

export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

export interface AssetImportResponse {
  dry_run: boolean;
  importable_count?: number;
  imported_count?: number;
  updated_count?: number;
  skipped_count: number;
  sheets: Record<string, number>;
  samples?: Array<Record<string, string>>;
}

export async function getAssets(params: { search?: string; page?: number } = {}) {
  const { data } = await api.get<PaginatedResponse<Asset>>("/assets/assets/", { params });
  return data;
}

export async function createAsset(payload: Partial<Asset>) {
  const { data } = await api.post<Asset>("/assets/assets/", payload);
  return data;
}

export async function updateAsset(id: number, payload: Partial<Asset>) {
  const { data } = await api.patch<Asset>(`/assets/assets/${id}/`, payload);
  return data;
}

export async function importAssetRegister(options: {
  file: File;
  dryRun: boolean;
}) {
  const formData = new FormData();
  formData.append("file", options.file);
  formData.append("dry_run", String(options.dryRun));

  const { data } = await api.post<AssetImportResponse>(
    "/assets/assets/import-register/",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );
  return data;
}
