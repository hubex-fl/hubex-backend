import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createApp, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import DashboardPage from "../DashboardPage.vue";

const flushPromises = () => new Promise<void>((r) => setTimeout(r, 0));

const METRICS = {
  devices: { total: 10, online: 7, stale: 2, offline: 1 },
  entities_total: 42,
  effects_total: 5,
  alerts: { firing: 3, acknowledged: 1 },
  events_24h: 256,
  webhooks_active: 2,
  uptime_seconds: 90061, // 1d 1h 1m
};

const ALERTS = [
  {
    id: 1,
    rule_id: 1,
    status: "firing",
    severity: "critical",
    message: "CPU high",
    fired_at: new Date().toISOString(),
  },
];

const EVENTS = [
  {
    id: 1,
    stream: "default",
    event_type: "device.online",
    payload: { uid: "dev-1" },
    created_at: new Date().toISOString(),
  },
];

function mockFetch(overrides: Partial<{ metrics: unknown; alerts: unknown; events: unknown }> = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input: RequestInfo | URL) => {
    const url = String(input);
    const json = (data: unknown) =>
      Promise.resolve(
        new Response(JSON.stringify(data), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );
    if (url.includes("/api/v1/metrics")) return json(overrides.metrics ?? METRICS);
    if (url.includes("/api/v1/alerts"))  return json(overrides.alerts  ?? ALERTS);
    if (url.includes("/api/v1/events"))  return json(overrides.events  ?? EVENTS);
    return json([]);
  });
}

function mountDashboard() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(DashboardPage);
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: "/",        component: DashboardPage },
      { path: "/pairing", component: { template: "<div/>" } },
      { path: "/devices", component: { template: "<div/>" } },
      { path: "/alerts",  component: { template: "<div/>" } },
    ],
  });
  app.use(router);
  app.mount(el);
  return { app, el, router };
}

describe("DashboardPage", () => {
  beforeEach(() => {
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("renders skeleton placeholders while loading", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
    const { app, el } = mountDashboard();
    expect(el.querySelector(".animate-pulse")).toBeTruthy();
    app.unmount();
  });

  it("renders all six metric cards after data loads", async () => {
    mockFetch();
    const { app, el, router } = mountDashboard();
    await router.isReady();
    await nextTick();
    await flushPromises();
    await nextTick();

    const text = el.textContent ?? "";
    expect(text).toContain("10");         // devices total
    expect(text).toContain("7");          // devices online
    expect(text).toContain("42");         // entities
    expect(text).toContain("3");          // active alerts
    expect(text).toContain("256");        // events 24h
    expect(text).toContain("1d 1h 1m");  // uptime
    app.unmount();
  });

  it("shows online percentage on the devices online card", async () => {
    mockFetch();
    const { app, el, router } = mountDashboard();
    await router.isReady();
    await nextTick();
    await flushPromises();
    await nextTick();

    expect(el.textContent).toContain("70%"); // 7/10 = 70%
    app.unmount();
  });

  it("renders device health ring SVG with segments", async () => {
    mockFetch();
    const { app, el, router } = mountDashboard();
    await router.isReady();
    await nextTick();
    await flushPromises();
    await nextTick();

    const svg = el.querySelector("svg[aria-label='Device health donut chart']");
    expect(svg).toBeTruthy();
    // background ring + 3 segments (online, stale, offline) = at least 3 circles
    const circles = svg?.querySelectorAll("circle");
    expect(circles?.length).toBeGreaterThanOrEqual(3);
    app.unmount();
  });

  it("ring SVG shows correct total in center", async () => {
    mockFetch();
    const { app, el, router } = mountDashboard();
    await router.isReady();
    await nextTick();
    await flushPromises();
    await nextTick();

    const svg = el.querySelector("svg[aria-label='Device health donut chart']");
    expect(svg?.textContent).toContain("10");
    app.unmount();
  });

  it("shows empty state when no alerts are firing", async () => {
    mockFetch({ alerts: [] });
    const { app, el, router } = mountDashboard();
    await router.isReady();
    await nextTick();
    await flushPromises();
    await nextTick();

    expect(el.textContent).toContain("No active alerts");
    app.unmount();
  });

  it("renders alert list when alerts exist", async () => {
    mockFetch();
    const { app, el, router } = mountDashboard();
    await router.isReady();
    await nextTick();
    await flushPromises();
    await nextTick();

    expect(el.textContent).toContain("CPU high");
    expect(el.textContent).toContain("critical");
    app.unmount();
  });

  it("renders event stream with events", async () => {
    mockFetch();
    const { app, el, router } = mountDashboard();
    await router.isReady();
    await nextTick();
    await flushPromises();
    await nextTick();

    expect(el.textContent).toContain("device.online");
    expect(el.textContent).toContain("default");
    app.unmount();
  });

  it("shows quick action buttons", async () => {
    mockFetch();
    const { app, el, router } = mountDashboard();
    await router.isReady();
    await nextTick();
    await flushPromises();
    await nextTick();

    expect(el.textContent).toContain("Pair Device");
    expect(el.textContent).toContain("Create Alert Rule");
    expect(el.textContent).toContain("View All Devices");
    app.unmount();
  });
});
