import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp } from "vue";
import TokenInspector from "../TokenInspector.vue";
import { clearToken, setToken } from "../../lib/api";

function mountPage() {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const app = createApp(TokenInspector);
  app.mount(el);
  return { app, el };
}

function makeToken(payload: Record<string, unknown>) {
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `x.${body}.y`;
}

afterEach(() => {
  clearToken();
  document.body.innerHTML = "";
  vi.useRealTimers();
});

describe("TokenInspector", () => {
  it("shows missing token state", () => {
    clearToken();
    const { app, el } = mountPage();
    expect(el.textContent).toContain("Token missing");
    app.unmount();
  });

  it("shows invalid token format", () => {
    setToken("not-a-jwt");
    const { app, el } = mountPage();
    expect(el.textContent).toContain("Invalid token format");
    app.unmount();
  });

  it("renders decoded fields and sorted caps", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
    const exp = Math.floor(Date.now() / 1000) + 3600;
    setToken(
      makeToken({
        sub: "3",
        iss: "hubex",
        jti: "abc",
        exp,
        caps: ["events.read", "devices.read"],
      })
    );

    const { app, el } = mountPage();
    expect(el.textContent).toContain("3");
    expect(el.textContent).toContain("hubex");
    expect(el.textContent).toContain("abc");
    expect(el.textContent).toContain(new Date(exp * 1000).toISOString());
    expect(el.textContent).toContain("devices.read, events.read");
    app.unmount();
  });
});
