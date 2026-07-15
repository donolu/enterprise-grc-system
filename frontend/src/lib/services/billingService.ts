import api from "@/lib/api";

export interface ModuleEntitlement {
  key: string;
  label: string;
  description: string;
  enabled: boolean;
}

export interface SubscriptionEntitlements {
  enabled_module_keys: string[];
  trial_module: string;
  module_catalog: ModuleEntitlement[];
}

export async function getCurrentSubscription() {
  const { data } = await api.get<SubscriptionEntitlements>("/billing/current_subscription/");
  return data;
}
