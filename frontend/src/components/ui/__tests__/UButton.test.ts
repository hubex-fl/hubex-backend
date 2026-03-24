import { describe, it, expect, afterEach } from "vitest";
import { createApp, defineComponent, h } from "vue";
import UButton from "../UButton.vue";

function mount(props: Record<string, unknown> = {}, slots: Record<string, () => unknown> = {}) {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const Wrapper = defineComponent({ render: () => h(UButton, props, slots) });
  createApp(Wrapper).mount(el);
  return el;
}

describe("UButton", () => {
  afterEach(() => { document.body.innerHTML = ""; });

  it("renders a button element", () => {
    const el = mount({}, { default: () => "Click me" });
    const btn = el.querySelector("button");
    expect(btn).not.toBeNull();
    expect(btn!.textContent?.trim()).toBe("Click me");
  });

  it("is disabled when loading", () => {
    const el = mount({ loading: true });
    expect(el.querySelector("button")!.disabled).toBe(true);
  });

  it("is disabled when disabled prop set", () => {
    const el = mount({ disabled: true });
    expect(el.querySelector("button")!.disabled).toBe(true);
  });

  it("shows spinner svg when loading", () => {
    const el = mount({ loading: true });
    expect(el.querySelector("svg.animate-spin")).not.toBeNull();
  });

  it("applies submit type", () => {
    const el = mount({ type: "submit" });
    expect(el.querySelector("button")!.type).toBe("submit");
  });

  it("defaults to type=button", () => {
    const el = mount({});
    expect(el.querySelector("button")!.type).toBe("button");
  });
});
