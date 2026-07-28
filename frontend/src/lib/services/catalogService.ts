import api from "@/lib/api";
import type { OperationResponse } from "@/lib/api/types";

export type TemplateImportResponse = OperationResponse<
  "catalogs_api_template_documents_import_library_create",
  200
>;

export type TemplateImportSample = NonNullable<TemplateImportResponse["samples"]>[number];

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
