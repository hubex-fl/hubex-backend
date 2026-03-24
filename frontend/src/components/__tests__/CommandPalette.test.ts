import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { createApp, defineComponent, h, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import { createPinia } from "pinia";
import CommandPalette from "../CommandPalette.vue";
import * as capMod from "../../lib/capabilities";

function mount(props: Record<string, unknown>) {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: "/", component: { template: "<div />" } },
      { path: "/devices", component: { template: "<div />" } },
      { path: "/events", component: { template: "<div />" } },
    ],
  });
  const pinia = createPinia();
  const Wrapper = defineComponent({ render: () => h(CommandPalette, props) });
  const app = createApp(Wrapper);
  app.use(router).use(pinia);
  app.mount(el);
  return { el, app, router };
}

describe("CommandPalette", () => {
  const caps = capMod.useCapabilities();

  beforeEach(() => {
    caps.status = "ready";
    caps.caps = new Set(["entities.read", "devices.read", "events.read", "effects.read", "tasks.read", "audit.read"]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("is not visible when open=false", () => {
    mount({ open: false, "onUpdate:open": vi.fn() });
    const input = document.body.querySelector("input");
    expect(input).toBeNull();
  });

  it("renders search input when open=true", async () => {
    mount({ open: true, "onUpdate:open": vi.fn() });
    await nextTick();
    const input = document.body.querySelector("input");
    expect(input).not.toBeNull();
  });

  it("filters results based on query", async () => {
    mount({ open: true, "onUpdate:open": vi.fn() });
    await nextTick();
    const input = document.body.querySelector("input") as HTMLInputElement;
    input.value = "devices";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await nextTick();
    const items = document.body.querySelectorAll("[role='option']");
    expect(items.length).toBeGreaterThan(0);
    const texts = Array.from(items).map((i) => i.textContent);
    const hasDevices = texts.some((t) => t?.toLowerCase().includes("device"));
    expect(hasDevices).toBe(true);
  });

  it("shows all commands when query is empty", async () => {
    mount({ open: true, "onUpdate:open": vi.fn() });
    await nextTick();
    const items = document.body.querySelectorAll("[role='option']");
    expect(items.length).toBeGreaterThan(3);
  });

  it("emits update:open=false when backdrop clicked", async () => {
    const onUpdate = vi.fn();
    mount({ open: true, "onUpdate:open": onUpdate });
    await nextTick();
    const backdrop = document.body.querySelector(".absolute.inset-0") as HTMLElement | null;
    expect(backdrop).not.toBeNull();
    backdrop!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await nextTick();
    expect(onUpdate).toHaveBeenCalledWith(false);
  });
});
