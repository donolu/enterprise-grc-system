import api from "@/lib/api";

export interface TemplateImportSample {
  title: string;
  module: string;
  document_type: string;
  source_filename: string;
  linkage_status: string;
}

export interface TemplateImportResponse {
  dry_run: boolean;
  importable_count?: number;
  imported_count?: number;
  updated_count?: number;
  skipped_count: number;
  total_importable?: number;
  modules: Record<string, number>;
  document_types: Record<string, number>;
  samples?: TemplateImportSample[];
}

export async function importTemplateLibrary(options: {
  file: File;
  dryRun: boolean;
  framework?: string;
  frameworkVersion?: string;
  module?: string;
  documentType?: string;
}): Promise<TemplateImportResponse> {
  const formData = new FormData();
  formData.append("file", options.file);
  formData.append("dry_run", String(options.dryRun));

  if (options.framework) {
    formData.append("framework", options.framework);
  }
  if (options.frameworkVersion) {
    formData.append("framework_version", options.frameworkVersion);
  }
  if (options.module) {
    formData.append("module", options.module);
  }
  if (options.documentType) {
    formData.append("document_type", options.documentType);
  }

  const { data } = await api.post<TemplateImportResponse>(
    "/catalogs/api/template-documents/import-library/",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );
  return data;
}
