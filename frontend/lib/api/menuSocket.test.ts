import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { subscribeToMenuUpdates } from "./menuSocket";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  closeCalls = 0;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close() {
    this.closeCalls += 1;
  }
}

describe("lib/api/menuSocket (T37, RF-6)", () => {
  const originalWebSocket = global.WebSocket;

  beforeEach(() => {
    FakeWebSocket.instances = [];
    // @ts-expect-error test double, not a full WebSocket implementation
    global.WebSocket = FakeWebSocket;
    vi.useFakeTimers();
  });

  afterEach(() => {
    global.WebSocket = originalWebSocket;
    vi.useRealTimers();
  });

  it("connects to /ws/menu/ and calls the callback on menu.actualizado", () => {
    const onMenuChanged = vi.fn();
    subscribeToMenuUpdates(onMenuChanged);

    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(FakeWebSocket.instances[0].url).toContain("/ws/menu/");

    FakeWebSocket.instances[0].onmessage?.({
      data: JSON.stringify({ type: "menu.actualizado" }),
    });
    expect(onMenuChanged).toHaveBeenCalledTimes(1);
  });

  it("ignores messages that are not menu.actualizado", () => {
    const onMenuChanged = vi.fn();
    subscribeToMenuUpdates(onMenuChanged);

    FakeWebSocket.instances[0].onmessage?.({
      data: JSON.stringify({ type: "otra.cosa" }),
    });
    expect(onMenuChanged).not.toHaveBeenCalled();
  });

  it("reconnects after the socket closes", async () => {
    subscribeToMenuUpdates(vi.fn());

    expect(FakeWebSocket.instances).toHaveLength(1);
    FakeWebSocket.instances[0].onclose?.();

    await vi.runOnlyPendingTimersAsync();
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("close() stops any further reconnection attempts", async () => {
    const handle = subscribeToMenuUpdates(vi.fn());

    handle.close();
    expect(FakeWebSocket.instances[0].closeCalls).toBe(1);

    FakeWebSocket.instances[0].onclose?.();
    await vi.runAllTimersAsync();
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
