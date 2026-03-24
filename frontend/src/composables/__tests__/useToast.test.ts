import { describe, it, expect, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useToast } from "../useToast";
import { useToastStore } from "../../stores/toast";

describe("useToast", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("success() adds a success toast", () => {
    const toast = useToast();
    const store = useToastStore();
    toast.success("It worked!");
    expect(store.toasts.length).toBe(1);
    expect(store.toasts[0].variant).toBe("success");
    expect(store.toasts[0].message).toBe("It worked!");
  });

  it("error() adds an error toast", () => {
    const toast = useToast();
    const store = useToastStore();
    toast.error("Something broke");
    expect(store.toasts[0].variant).toBe("error");
  });

  it("warn() adds a warn toast", () => {
    const toast = useToast();
    const store = useToastStore();
    toast.warn("Be careful");
    expect(store.toasts[0].variant).toBe("warn");
  });

  it("info() adds an info toast", () => {
    const toast = useToast();
    const store = useToastStore();
    toast.info("FYI");
    expect(store.toasts[0].variant).toBe("info");
  });

  it("add() uses provided variant", () => {
    const toast = useToast();
    const store = useToastStore();
    toast.add("Custom", "warn");
    expect(store.toasts[0].message).toBe("Custom");
    expect(store.toasts[0].variant).toBe("warn");
  });
});
