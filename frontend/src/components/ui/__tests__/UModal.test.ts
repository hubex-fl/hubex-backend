import { describe, it, expect, vi, afterEach } from "vitest";
import { createApp, defineComponent, h, nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import UModal from "../UModal.vue";

function mount(props: Record<string, unknown>, slots: Record<string, () => unknown> = {}) {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const router = createRouter({ history: createWebHistory(), routes: [{ path: "/", component: { template: "<div />" } }] });
  const Wrapper = defineComponent({ render: () => h(UModal, props, slots) });
  const app = createApp(Wrapper);
  app.use(router);
  app.mount(el);
  return { el, app };
}

describe("UModal", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  it("renders nothing when open=false", () => {
    mount({ open: false });
    const dialog = document.body.querySelector("[role='dialog']");
    expect(dialog).toBeNull();
  });

  it("renders dialog when open=true", async () => {
    mount({ open: true, title: "Test Modal" });
    await nextTick();
    const dialog = document.body.querySelector("[role='dialog']");
    expect(dialog).not.toBeNull();
  });

  it("shows title text", async () => {
    mount({ open: true, title: "Hello World" });
    await nextTick();
    expect(document.body.textContent).toContain("Hello World");
  });

  it("emits close when close button clicked", async () => {
    const onClose = vi.fn();
    mount({ open: true, title: "T", onClose }, { default: () => "body" });
    await nextTick();
    const closeBtn = Array.from(document.body.querySelectorAll("button")).find(
      (b) => b.getAttribute("aria-label") === "Close"
    );
    expect(closeBtn).not.toBeNull();
    closeBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await nextTick();
    expect(onClose).toHaveBeenCalled();
  });

  it("emits close when backdrop clicked", async () => {
    const onClose = vi.fn();
    mount({ open: true, onClose }, { default: () => "body" });
    await nextTick();
    const backdrop = document.body.querySelector(".absolute.inset-0") as HTMLElement | null;
    expect(backdrop).not.toBeNull();
    backdrop!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await nextTick();
    expect(onClose).toHaveBeenCalled();
  });

  it("renders slot content", async () => {
    mount({ open: true }, { default: () => "slot content here" });
    await nextTick();
    expect(document.body.textContent).toContain("slot content here");
  });
});
