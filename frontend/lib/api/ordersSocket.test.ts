import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { subscribeToOrderUpdates } from "./ordersSocket";

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

describe("lib/api/ordersSocket (T63, soporte RF-9/RF-11)", () => {
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

  it("connects to /ws/pedidos/ and calls the callback on pedidos.actualizado", () => {
    const onOrdersChanged = vi.fn();
    subscribeToOrderUpdates(onOrdersChanged);

    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(FakeWebSocket.instances[0].url).toContain("/ws/pedidos/");

    FakeWebSocket.instances[0].onmessage?.({
      data: JSON.stringify({ type: "pedidos.actualizado" }),
    });
    expect(onOrdersChanged).toHaveBeenCalledTimes(1);
  });

  it("ignores messages that are not pedidos.actualizado", () => {
    const onOrdersChanged = vi.fn();
    subscribeToOrderUpdates(onOrdersChanged);

    FakeWebSocket.instances[0].onmessage?.({
      data: JSON.stringify({ type: "otra.cosa" }),
    });
    expect(onOrdersChanged).not.toHaveBeenCalled();
  });

  it("reconnects after the socket closes", async () => {
    subscribeToOrderUpdates(vi.fn());

    expect(FakeWebSocket.instances).toHaveLength(1);
    FakeWebSocket.instances[0].onclose?.();

    await vi.runOnlyPendingTimersAsync();
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("close() stops any further reconnection attempts", async () => {
    const handle = subscribeToOrderUpdates(vi.fn());

    handle.close();
    expect(FakeWebSocket.instances[0].closeCalls).toBe(1);

    FakeWebSocket.instances[0].onclose?.();
    await vi.runAllTimersAsync();
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  // T94 — causa 2 del escenario "un pedido apareció mucho después": si el
  // socket se cae (PC suspendido, Wi-Fi) y reconecta, los cambios ocurridos
  // mientras estuvo desconectado no se piden; al reconectar se vuelve a
  // pedir la lista.
  it("asks for the list again after reconnecting, to catch missed changes (T94)", async () => {
    const onOrdersChanged = vi.fn();
    subscribeToOrderUpdates(onOrdersChanged);
    FakeWebSocket.instances[0].onopen?.();

    FakeWebSocket.instances[0].onclose?.();
    await vi.runOnlyPendingTimersAsync();
    FakeWebSocket.instances[1].onopen?.();

    expect(onOrdersChanged).toHaveBeenCalledTimes(1);
  });

  it("does not ask for the list on the first connection (T94)", () => {
    const onOrdersChanged = vi.fn();
    subscribeToOrderUpdates(onOrdersChanged);
    FakeWebSocket.instances[0].onopen?.();
    expect(onOrdersChanged).not.toHaveBeenCalled();
  });
});
