import { apiFetch } from "./api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface VariablePattern {
  variable_key: string;
  pattern:
    | "sine"
    | "random_walk"
    | "step"
    | "ramp"
    | "counter"
    | "gps_track"
    | "noise"
    | "formula"
    | "csv_replay"
    | "manual";
  config: Record<string, unknown>;
}

export interface SimulatorConfig {
  id: number;
  name: string;
  description: string | null;
  template: string | null;
  device_id: number | null;
  device_uid: string | null;
  variable_patterns: VariablePattern[];
  interval_seconds: number;
  speed_multiplier: number;
  is_active: boolean;
  is_virtual_device: boolean;
  total_points_sent: number;
  started_at: string | null;
  last_value_at: string | null;
}

export interface SimulatorTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  variable_patterns: VariablePattern[];
}

export interface SimulatorCreate {
  name: string;
  description?: string | null;
  template?: string | null;
  device_uid?: string | null;
  variable_patterns: VariablePattern[];
  interval_seconds?: number;
  speed_multiplier?: number;
  is_virtual_device?: boolean;
  auto_start?: boolean;
}

export interface SimulatorUpdate {
  name?: string;
  description?: string | null;
  variable_patterns?: VariablePattern[];
  interval_seconds?: number;
  speed_multiplier?: number;
}

// ── API ──────────────────────────────────────────────────────────────────────

const BASE = "/api/v1/simulator/configs";

export async function listSimulators(): Promise<SimulatorConfig[]> {
  return apiFetch<SimulatorConfig[]>(BASE);
}

export async function createSimulator(data: SimulatorCreate): Promise<SimulatorConfig> {
  return apiFetch<SimulatorConfig>(BASE, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSimulator(id: number, data: SimulatorUpdate): Promise<SimulatorConfig> {
  return apiFetch<SimulatorConfig>(`${BASE}/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteSimulator(id: number): Promise<void> {
  await apiFetch<void>(`${BASE}/${id}`, { method: "DELETE" });
}

export async function startSimulator(id: number): Promise<SimulatorConfig> {
  return apiFetch<SimulatorConfig>(`${BASE}/${id}/start`, { method: "POST" });
}

export async function stopSimulator(id: number): Promise<SimulatorConfig> {
  return apiFetch<SimulatorConfig>(`${BASE}/${id}/stop`, { method: "POST" });
}

export async function pulseValue(
  id: number,
  variableKey: string,
  value: number,
): Promise<void> {
  await apiFetch<void>(`${BASE}/${id}/pulse`, {
    method: "POST",
    body: JSON.stringify({ variable_key: variableKey, value }),
  });
}

export async function getTemplates(): Promise<SimulatorTemplate[]> {
  return apiFetch<SimulatorTemplate[]>("/api/v1/simulator/templates");
}

// ── Client-side pattern preview generators ──────────────────────────────────

/** Generate ~30s of sample data for client-side sparkline preview */
export function generatePreview(
  pattern: VariablePattern["pattern"],
  config: Record<string, unknown>,
  points = 60,
): { t: number; v: number }[] {
  const now = Date.now();
  const data: { t: number; v: number }[] = [];

  for (let i = 0; i < points; i++) {
    const t = now - (points - i) * 500;
    const sec = i * 0.5;
    let v = 0;

    switch (pattern) {
      case "sine": {
        const min = (config.min as number) ?? 0;
        const max = (config.max as number) ?? 100;
        const period = (config.period as number) ?? 60;
        const phase = (config.phase_offset as number) ?? 0;
        const mid = (min + max) / 2;
        const amp = (max - min) / 2;
        v = mid + amp * Math.sin((2 * Math.PI * sec) / period + phase);
        break;
      }
      case "random_walk": {
        const center = (config.center as number) ?? 50;
        const volatility = (config.volatility as number) ?? 5;
        const minB = (config.min_bound as number) ?? 0;
        const maxB = (config.max_bound as number) ?? 100;
        if (i === 0) v = center;
        else v = data[i - 1].v + (Math.random() - 0.5) * volatility;
        v = Math.max(minB, Math.min(maxB, v));
        break;
      }
      case "step": {
        const valuesStr = (config.values as string) ?? "0,50,100";
        const values = valuesStr
          .split(",")
          .map((s: string) => parseFloat(s.trim()))
          .filter((n: number) => !isNaN(n));
        const interval = (config.interval as number) ?? 5;
        if (values.length > 0) {
          const idx = Math.floor(sec / interval) % values.length;
          v = values[idx];
        }
        break;
      }
      case "ramp": {
        const start = (config.start as number) ?? 0;
        const end = (config.end as number) ?? 100;
        const duration = (config.duration as number) ?? 30;
        const loop = (config.loop as boolean) ?? true;
        const progress = loop ? (sec % duration) / duration : Math.min(sec / duration, 1);
        v = start + (end - start) * progress;
        break;
      }
      case "counter": {
        const startVal = (config.start as number) ?? 0;
        const increment = (config.increment as number) ?? 1;
        const resetAt = (config.reset_at as number) ?? 1000;
        v = (startVal + i * increment) % resetAt;
        break;
      }
      case "noise": {
        const center = (config.center as number) ?? 50;
        const amplitude = (config.amplitude as number) ?? 10;
        v = center + (Math.random() - 0.5) * 2 * amplitude;
        break;
      }
      case "formula": {
        try {
          const expr = (config.expression as string) ?? "sin(t)";
          const fn = new Function(
            "t",
            "sin",
            "cos",
            "random",
            "pi",
            "abs",
            "sqrt",
            `return (${expr})`,
          );
          v = fn(sec, Math.sin, Math.cos, Math.random, Math.PI, Math.abs, Math.sqrt) as number;
          if (!isFinite(v)) v = 0;
        } catch {
          v = 0;
        }
        break;
      }
      case "gps_track":
        // GPS generates lat/lng, just show a sine-like path for preview
        v = 48.2 + 0.01 * Math.sin((2 * Math.PI * sec) / 30);
        break;
      case "csv_replay":
        // CSV replay can't be previewed client-side; show placeholder
        v = 50 + 20 * Math.sin((2 * Math.PI * sec) / 20);
        break;
      case "manual":
        v = (config.initial_value as number) ?? 0;
        break;
      default:
        v = 0;
    }

    data.push({ t, v });
  }
  return data;
}

// ── Pattern metadata ────────────────────────────────────────────────────────

export const PATTERN_OPTIONS: {
  value: VariablePattern["pattern"];
  label: string;
  labelDe: string;
}[] = [
  { value: "sine", label: "Sine Wave", labelDe: "Sinuswelle" },
  { value: "random_walk", label: "Random Walk", labelDe: "Random Walk" },
  { value: "step", label: "Step", labelDe: "Stufe" },
  { value: "ramp", label: "Ramp", labelDe: "Rampe" },
  { value: "counter", label: "Counter", labelDe: "Zaehler" },
  { value: "gps_track", label: "GPS Track", labelDe: "GPS-Track" },
  { value: "noise", label: "Noise", labelDe: "Rauschen" },
  { value: "formula", label: "Custom Formula", labelDe: "Formel" },
  { value: "csv_replay", label: "CSV Replay", labelDe: "CSV-Wiedergabe" },
  { value: "manual", label: "Manual", labelDe: "Manuell" },
];

// ── Built-in templates (client-side fallback) ───────────────────────────────

export const BUILTIN_TEMPLATES: SimulatorTemplate[] = [
  {
    id: "temperature",
    name: "Temperature Sensor",
    description: "Simulates a room temperature sensor with natural fluctuations",
    icon: "thermometer",
    variable_patterns: [
      { variable_key: "temperature", pattern: "sine", config: { min: 18, max: 28, period: 300 } },
      { variable_key: "humidity", pattern: "random_walk", config: { center: 55, volatility: 2, min_bound: 30, max_bound: 80 } },
    ],
  },
  {
    id: "energy",
    name: "Energy Meter",
    description: "Simulates power consumption with daily cycles",
    icon: "bolt",
    variable_patterns: [
      { variable_key: "power_watts", pattern: "sine", config: { min: 200, max: 3500, period: 600 } },
      { variable_key: "energy_kwh", pattern: "counter", config: { start: 0, increment: 0.5, reset_at: 10000 } },
    ],
  },
  {
    id: "gps",
    name: "GPS Tracker",
    description: "Simulates a moving vehicle with GPS coordinates",
    icon: "map-pin",
    variable_patterns: [
      { variable_key: "latitude", pattern: "gps_track", config: { waypoints: "48.2082,16.3738;48.2100,16.3800;48.2050,16.3850" } },
      { variable_key: "longitude", pattern: "gps_track", config: { waypoints: "16.3738,48.2082;16.3800,48.2100;16.3850,48.2050" } },
      { variable_key: "speed_kmh", pattern: "random_walk", config: { center: 40, volatility: 8, min_bound: 0, max_bound: 120 } },
    ],
  },
  {
    id: "motion",
    name: "Motion Sensor",
    description: "Simulates a PIR motion detector with binary events",
    icon: "activity",
    variable_patterns: [
      { variable_key: "motion_detected", pattern: "step", config: { values: "0,0,0,1,0,0,1", interval: 10 } },
      { variable_key: "lux", pattern: "random_walk", config: { center: 300, volatility: 20, min_bound: 0, max_bound: 1000 } },
    ],
  },
  {
    id: "weather",
    name: "Weather Station",
    description: "Simulates outdoor weather with multiple sensors",
    icon: "cloud-sun",
    variable_patterns: [
      { variable_key: "temperature", pattern: "sine", config: { min: -5, max: 35, period: 600 } },
      { variable_key: "humidity", pattern: "random_walk", config: { center: 60, volatility: 3, min_bound: 20, max_bound: 95 } },
      { variable_key: "pressure_hpa", pattern: "sine", config: { min: 990, max: 1030, period: 900 } },
      { variable_key: "wind_speed", pattern: "noise", config: { center: 12, amplitude: 8 } },
    ],
  },
  // Sprint 8 R4 Bucket C F19: new templates that line up with the
  // expanded Sprint 5b hardware component catalog (BME280 / BH1750 /
  // HC-SR04 / servo / LED PWM / door contact). These round out the
  // hardware-demo story in the Sandbox.
  {
    id: "bme280",
    name: "BME280 Environmental",
    description: "BME280 I2C sensor — temperature, humidity, pressure, and IAQ gas resistance",
    icon: "thermometer",
    variable_patterns: [
      { variable_key: "temperature", pattern: "sine", config: { min: 19, max: 24.5, period: 300 } },
      { variable_key: "humidity", pattern: "sine", config: { min: 42, max: 58, period: 300, phase_offset: 3.14159 } },
      { variable_key: "pressure", pattern: "noise", config: { center: 1013.25, amplitude: 3.5 } },
      { variable_key: "gas_resistance_kohm", pattern: "random_walk", config: { center: 150, volatility: 12, min_bound: 50, max_bound: 400 } },
    ],
  },
  {
    id: "bh1750",
    name: "BH1750 Light Sensor",
    description: "BH1750 ambient light meter with a day/night lux cycle",
    icon: "sun",
    variable_patterns: [
      { variable_key: "lux", pattern: "sine", config: { min: 0, max: 1200, period: 300 } },
    ],
  },
  {
    id: "ultrasonic",
    name: "HC-SR04 Distance",
    description: "Ultrasonic distance sensor with presence spikes on top of a random-walk baseline",
    icon: "ruler",
    variable_patterns: [
      { variable_key: "distance_cm", pattern: "random_walk", config: { center: 85, volatility: 18, min_bound: 4, max_bound: 200 } },
      { variable_key: "object_detected", pattern: "step", config: { values: "0,0,1,0,0,0,1,0", interval: 15 } },
    ],
  },
  {
    id: "servo",
    name: "Servo Motor",
    description: "Servo actuator sweeping between set-points with a matching target channel",
    icon: "rotate-cw",
    variable_patterns: [
      { variable_key: "angle_deg", pattern: "sine", config: { min: 0, max: 180, period: 120 } },
      { variable_key: "target_angle_deg", pattern: "step", config: { values: "0,45,90,135,180,135,90,45", interval: 15 } },
    ],
  },
  {
    id: "led_pwm",
    name: "LED Dimmer (PWM)",
    description: "PWM LED channel — brightness ramps and duty-cycle pulses",
    icon: "lightbulb",
    variable_patterns: [
      { variable_key: "brightness_pct", pattern: "sine", config: { min: 0, max: 100, period: 300 } },
      { variable_key: "duty_cycle", pattern: "ramp", config: { start: 0, end: 255, duration: 600, loop: true } },
    ],
  },
  {
    id: "door_contact",
    name: "Door/Window Contact",
    description: "Reed-switch contact sensor — open/closed events plus battery drain",
    icon: "door-open",
    variable_patterns: [
      { variable_key: "contact_closed", pattern: "step", config: { values: "1,1,1,0,1,1,0,1", interval: 45 } },
      { variable_key: "battery_pct", pattern: "ramp", config: { start: 100, end: 0, duration: 2592000, loop: true } },
    ],
  },
  {
    id: "custom",
    name: "Custom",
    description: "Start from scratch with an empty simulator",
    icon: "wrench",
    variable_patterns: [],
  },
];
