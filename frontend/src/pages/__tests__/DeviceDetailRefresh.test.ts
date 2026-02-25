import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";

const flushPromises = () => Promise.resolve();

async function mountDetail() {
  vi.resetModules();
  const apiFetch = vi.fn(async (path: string) => {
    if (path.includes("/current-task")) {
      return {
        has_active_lease: false,
        device_id: 1,
        task_id: null,
        task_name: null,
        task_type: null,
        task_status: null,
        claimed_at: null,
        lease_expires_at: null,
        lease_seconds_remaining: null,
        lease_token_hint: null,
        context_key: null,
      };
    }
    if (path.includes("/task-history")) {
      return [
        {
          task_id: 11,
          task_name: "Demo Task",
          task_type: "demo",
          task_status: "completed",
          claimed_at: "2026-02-01T00:00:00Z",
          finished_at: "2026-02-01T00:00:10Z",
          last_seen_at: null,
        },
      ];
    }
    if (path.includes("/variables/applied")) return [];
    if (path.startsWith("/api/v1/devices/")) {
      return {
        id: 1,
        device_uid: "dev-1",
        last_seen_at: "2026-02-01T00:00:00Z",
        health: "ok",
        last_seen_age_seconds: 10,
        state: "claimed",
        pairing_active: false,
        busy: false,
      };
    }
    return {};
  });

  vi.doMock("../../lib/api", () => ({
    apiFetch,
    getToken: () => null,
    reissueDeviceToken: vi.fn(),
  }));
  vi.doMock("../../lib/variables", () => ({
    getEffectiveVariables: vi.fn().mockResolvedValue({ items: [], snapshot_id: null }),
    putValue: vi.fn(),
  }));
  vi.doMock("../../lib/errors", () => ({
    mapErrorToUserText: (_info: any, fallback: string) => fallback,
    parseApiError: () => ({}),
  }));
  vi.doMock("../../lib/capabilities", () => {
    const state = { status: "ready", caps: new Set<string>(), error: null };
    return {
      useCapabilities: () => state,
      hasCap: () => false,
      refreshCapabilities: vi.fn(),
    };
  });

  const DeviceDetail = (await import("../DeviceDetail.vue")).default;
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: "/devices/:id", component: DeviceDetail }],
  });
  await router.push("/devices/1");
  await router.isReady();

  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(DeviceDetail);
  app.use(router);
  app.mount(el);

  await nextTick();
  await flushPromises();
  return { app, el };
}

function findTaskTable(el: HTMLElement): HTMLTableElement | null {
  const tables = Array.from(el.querySelectorAll("table"));
  return (
    tables.find((table) =>
      table.textContent?.includes("Task") && table.textContent?.includes("Status")
    ) ?? null
  );
}

function findTelemetryTable(el: HTMLElement): HTMLTableElement | null {
  const tables = Array.from(el.querySelectorAll("table"));
  return (
    tables.find((table) =>
      table.textContent?.includes("Payload") && table.textContent?.includes("Type")
    ) ?? null
  );
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("DeviceDetail refresh", () => {
  it("keeps task and telemetry tables mounted across poll", async () => {
    vi.useFakeTimers();
    const { app, el } = await mountDetail();
    await nextTick();
    await flushPromises();

    const taskTableBefore = findTaskTable(el);
    const telemetryTableBefore = findTelemetryTable(el);
    expect(taskTableBefore).toBeTruthy();
    expect(telemetryTableBefore).toBeTruthy();

    await vi.advanceTimersByTimeAsync(2600);
    await flushPromises();

    const taskTableAfter = findTaskTable(el);
    const telemetryTableAfter = findTelemetryTable(el);
    expect(taskTableAfter).toBe(taskTableBefore);
    expect(telemetryTableAfter).toBe(telemetryTableBefore);

    app.unmount();
  });

  it("buckets relative time output", async () => {
    vi.useFakeTimers();
    const { app } = await mountDetail();
    const instance = (app as any)._instance;
    const fmtAgoFromIso = instance?.setupState?.fmtAgoFromIso as (iso: string | null) => string;
    expect(typeof fmtAgoFromIso).toBe("function");

    vi.setSystemTime(new Date("2026-02-01T00:00:12Z"));
    const iso = "2026-02-01T00:00:00Z";
    const first = fmtAgoFromIso(iso);

    vi.setSystemTime(new Date("2026-02-01T00:00:13Z"));
    const second = fmtAgoFromIso(iso);

    expect(first).toBe(second);
    app.unmount();
  });
});
