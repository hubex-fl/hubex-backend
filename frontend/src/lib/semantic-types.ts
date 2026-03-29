import { apiFetch } from './api';

export interface SemanticType {
  id: number;
  name: string;
  display_name: string;
  base_type: 'bool' | 'int' | 'float' | 'string' | 'json';
  unit: string | null;
  unit_symbol: string | null;
  value_schema: Record<string, any> | null;
  min_value: number | null;
  max_value: number | null;
  default_viz_type: string | null;
  icon: string | null;
  color: string | null;
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
}

export interface TriggerTemplate {
  id: number;
  semantic_type_id: number;
  trigger_name: string;
  display_name: string;
  description: string | null;
  config_schema: Record<string, any> | null;
  icon: string | null;
}

export interface UnitConversion {
  id: number;
  semantic_type_id: number;
  from_unit: string;
  to_unit: string;
  formula: string;
  is_default: boolean;
}

export interface SemanticTypeCreate {
  name: string;
  display_name: string;
  base_type: string;
  unit?: string;
  unit_symbol?: string;
  min_value?: number;
  max_value?: number;
  default_viz_type?: string;
  icon?: string;
  color?: string;
}

const BASE = '/api/v1/types/semantic';

export async function listSemanticTypes(params?: { builtin?: boolean; base_type?: string }): Promise<SemanticType[]> {
  const query = new URLSearchParams();
  if (params?.builtin !== undefined) query.set('builtin', String(params.builtin));
  if (params?.base_type) query.set('base_type', params.base_type);
  const qs = query.toString();
  return apiFetch(`${BASE}${qs ? '?' + qs : ''}`);
}

export async function getSemanticType(id: number): Promise<SemanticType> {
  return apiFetch(`${BASE}/${id}`);
}

export async function createSemanticType(data: SemanticTypeCreate): Promise<SemanticType> {
  return apiFetch(BASE, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateSemanticType(id: number, data: Partial<SemanticTypeCreate>): Promise<SemanticType> {
  return apiFetch(`${BASE}/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function deleteSemanticType(id: number): Promise<void> {
  await apiFetch(`${BASE}/${id}`, { method: 'DELETE' });
}

export async function getTypeTriggers(id: number): Promise<TriggerTemplate[]> {
  return apiFetch(`${BASE}/${id}/triggers`);
}

export async function getTypeConversions(id: number): Promise<UnitConversion[]> {
  return apiFetch(`${BASE}/${id}/conversions`);
}
