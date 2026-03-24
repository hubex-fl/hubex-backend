import { describe, it, expect, afterEach } from "vitest";
import { createApp, defineComponent, h, nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { useToastStore } from "../../../stores/toast";
import UToast from "../UToast.vue";

function mountToast() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(defineComponent({ render: () => h(UToast) }));
  app.use(pinia);
  app.mount(el);
  return { el, app, store: useToastStore() };
}

describe("UToast", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  it("renders no toasts initially", () => {
    mountToast();
    expect(document.body.querySelectorAll("[role='alert']").length).toBe(0);
  });

  it("renders a toast when added", async () => {
    const { store } = mountToast();
    store.addToast("Hello toast", "success", 0);
    await nextTick();
    expect(document.body.querySelectorAll("[role='alert']").length).toBe(1);
    expect(document.body.textContent).toContain("Hello toast");
  });

  it("dismiss button calls store.removeToast", async () => {
    const { store } = mountToast();
    store.addToast("Dismiss me", "info", 0);
    await nextTick();
    const dismissBtn = Array.from(document.body.querySelectorAll("button")).find(
      (b) => b.getAttribute("aria-label") === "Dismiss"
    );
    expect(dismissBtn).not.toBeNull();
    dismissBtn!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await nextTick();
    // Store should have the toast removed
    expect(store.toasts.length).toBe(0);
  });

  it("renders multiple toasts", async () => {
    const { store } = mountToast();
    store.addToast("First", "success", 0);
    store.addToast("Second", "error", 0);
    await nextTick();
    expect(document.body.querySelectorAll("[role='alert']").length).toBe(2);
  });
});
