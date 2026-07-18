import api from "@/lib/api";
import type {
  OperationQuery,
  OperationRequestBody,
  OperationResponse,
} from "@/lib/api/types";

type AssetListResponse = OperationResponse<"assets_assets_list", 200>;

export type Asset = AssetListResponse["results"][number];
export type AssetCreatePayload = OperationRequestBody<"assets_assets_create">;
export type AssetUpdatePayload = OperationRequestBody<"assets_assets_partial_update">;
export type PaginatedResponse<T> = Omit<AssetListResponse, "results"> & {
  results: T[];
};

export interface AssetImportResponse {
  dry_run: boolean;
  importable_count?: number;
  imported_count?: number;
  updated_count?: number;
  skipped_count: number;
  sheets: Record<string, number>;
  samples?: Array<Record<string, string>>;
}

export async function getAssets(params: OperationQuery<"assets_assets_list"> = {}) {
  const { data } = await api.get<AssetListResponse>("/assets/assets/", { params });
  return data;
}

export async function createAsset(payload: AssetCreatePayload) {
  const { data } = await api.post<OperationResponse<"assets_assets_create", 201>>(
    "/assets/assets/",
    payload,
  );
  return data;
}

export async function updateAsset(id: number, payload: AssetUpdatePayload) {
  const { data } = await api.patch<OperationResponse<"assets_assets_partial_update", 200>>(
    `/assets/assets/${id}/`,
    payload,
  );
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
