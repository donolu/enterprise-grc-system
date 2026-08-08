import api from "@/lib/api";
import type { OperationRequestBody, OperationResponse } from "@/lib/api/types";

export type TenantEmailSettings = OperationResponse<"tenant_email_settings_retrieve", 200>;
export type TenantEmailSettingsPayload = OperationRequestBody<
  "tenant_email_settings_partial_update"
>;
export type SenderVerificationResponse = OperationResponse<
  "tenant_email_settings_verification_create",
  202
>;

export async function getTenantEmailSettings() {
  const { data } = await api.get<TenantEmailSettings>("/tenant-email-settings/");
  return data;
}

export async function updateTenantEmailSettings(payload: TenantEmailSettingsPayload) {
  const { data } = await api.patch<TenantEmailSettings>(
    "/tenant-email-settings/",
    payload,
  );
  return data;
}

export async function requestTenantEmailVerification() {
  const { data } = await api.post<SenderVerificationResponse>(
    "/tenant-email-settings/verification/",
  );
  return data;
}

export async function confirmTenantEmailVerification(token: string) {
  const { data } = await api.post<
    OperationResponse<"tenant_email_settings_verification_confirm_create", 200>
  >("/tenant-email-settings/verification/confirm/", { token });
  return data;
}
