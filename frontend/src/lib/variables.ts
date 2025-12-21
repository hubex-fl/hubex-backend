import { apiFetch } from "./api";

export type VariableScope = "device" | "global";
export type VariableValueType = "string" | "int" | "float" | "bool" | "json";

export type VariableDefinition = {
  key: string;
  scope: VariableScope;
  value_type: VariableValueType;
  default_value: any | null;
  description: string | null;
  is_secret: boolean;
  is_readonly: boolean;
  created_at: string;
  updated_at: string;
};

export type VariableValue = {
  key: string;
  scope: VariableScope;
  device_uid: string | null;
  value: any;
  version: number | null;
  updated_at: string | null;
  is_secret: boolean;
};

export type DeviceVariables = {
  device_uid: string;
  globals: VariableValue[];
  device: VariableValue[];
};

export type VariableAudit = {
  variable_key: string;
  scope: VariableScope;
  device_uid: string | null;
  old_value: any | null;
  new_value: any | null;
  old_version: number | null;
  new_version: number | null;
  actor_type: string;
  actor_user_id: number | null;
  actor_device_id: number | null;
  request_id: string | null;
  note: string | null;
  created_at: string;
};

export type VariableValueInput = {
  key: string;
  scope: VariableScope;
  deviceUid?: string | null;
  value: any;
  expectedVersion?: number | null;
};

export type VariableDefinitionInput = {
  key: string;
  scope: VariableScope;
  valueType: VariableValueType;
  defaultValue?: any | null;
  description?: string | null;
  isSecret?: boolean;
  isReadonly?: boolean;
};

export async function listDefinitions(scope?: VariableScope): Promise<VariableDefinition[]> {
  const path = scope ? `/api/v1/variables/definitions?scope=${scope}` : "/api/v1/variables/definitions";
  return apiFetch<VariableDefinition[]>(path);
}

export async function createDefinition(input: VariableDefinitionInput): Promise<VariableDefinition> {
  return apiFetch<VariableDefinition>("/api/v1/variables/definitions", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getValue(params: {
  key: string;
  scope: VariableScope;
  deviceUid?: string | null;
}): Promise<VariableValue> {
  const query = new URLSearchParams();
  query.set("key", params.key);
  query.set("scope", params.scope);
  if (params.deviceUid) query.set("deviceUid", params.deviceUid);
  return apiFetch<VariableValue>(`/api/v1/variables/value?${query.toString()}`);
}

export async function putValue(input: VariableValueInput): Promise<VariableValue> {
  return apiFetch<VariableValue>("/api/v1/variables/value", {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export async function getDeviceVariables(deviceUid: string): Promise<DeviceVariables> {
  return apiFetch<DeviceVariables>(`/api/v1/variables/device/${deviceUid}`);
}

export async function getAudit(params: {
  key: string;
  scope?: VariableScope;
  deviceUid?: string | null;
  limit?: number;
  offset?: number;
}): Promise<VariableAudit[]> {
  const query = new URLSearchParams();
  query.set("key", params.key);
  if (params.scope) query.set("scope", params.scope);
  if (params.deviceUid) query.set("deviceUid", params.deviceUid);
  if (params.limit) query.set("limit", String(params.limit));
  if (params.offset) query.set("offset", String(params.offset));
  return apiFetch<VariableAudit[]>(`/api/v1/variables/audit?${query.toString()}`);
}
