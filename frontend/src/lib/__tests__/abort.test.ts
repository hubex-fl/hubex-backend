import { describe, expect, it } from "vitest";
import { createApp, defineComponent } from "vue";
import { useAbortHandle } from "../abort";

describe("useAbortHandle", () => {
  it("aborts on unmount", () => {
    let signal: AbortSignal | null = null;
    const Comp = defineComponent({
      setup() {
        const handle = useAbortHandle();
        signal = handle.signal;
        return () => null;
      },
    });

    const el = document.createElement("div");
    document.body.appendChild(el);
    const app = createApp(Comp);
    app.mount(el);
    expect(signal?.aborted).toBe(false);
    app.unmount();
    expect(signal?.aborted).toBe(true);
  });
});
