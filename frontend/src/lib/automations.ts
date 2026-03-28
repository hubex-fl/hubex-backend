import { apiFetch } from "./api";

const BASE = "/api/v1/automations";

export interface AutomationRuleOut {
  id: number;
  org_id: number | null;
  name: string;
  description: string | null;
  enabled: boolean;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  action_type: string;
  action_config: Record<string, unknown>;
  cooldown_seconds: number;
  fire_count: number;
  last_fired_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationRuleCreate {
  name: string;
  description?: string | null;
  enabled: boolean;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  action_type: string;
  action_config: Record<string, unknown>;
  cooldown_seconds: number;
}

export interface AutomationRulePatch {
  name?: string;
  description?: string | null;
  enabled?: boolean;
  trigger_type?: string;
  trigger_config?: Record<string, unknown>;
  action_type?: string;
  action_config?: Record<string, unknown>;
  cooldown_seconds?: number;
}

export interface AutomationFireLogOut {
  id: number;
  rule_id: number;
  fired_at: string;
  success: boolean;
  error_message: string | null;
  context_json: Record<string, unknown>;
}

export async function listAutomations(params?: { enabled?: boolean }): Promise<AutomationRuleOut[]> {
  const qs = params?.enabled !== undefined ? `?enabled=${params.enabled}` : "";
  return apiFetch<AutomationRuleOut[]>(`${BASE}${qs}`);
}

export async function createAutomation(data: AutomationRuleCreate): Promise<AutomationRuleOut> {
  return apiFetch<AutomationRuleOut>(BASE, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateAutomation(id: number, data: AutomationRulePatch): Promise<AutomationRuleOut> {
  return apiFetch<AutomationRuleOut>(`${BASE}/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteAutomation(id: number): Promise<void> {
  await apiFetch<void>(`${BASE}/${id}`, { method: "DELETE" });
}

export async function testAutomation(id: number): Promise<{ success: boolean; message: string }> {
  return apiFetch<{ success: boolean; message: string }>(`${BASE}/${id}/test`, {
    method: "POST",
  });
}

export async function getAutomationHistory(id: number): Promise<AutomationFireLogOut[]> {
  return apiFetch<AutomationFireLogOut[]>(`${BASE}/${id}/history`);
}
