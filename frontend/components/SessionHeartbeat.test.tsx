import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { SessionHeartbeat } from "./SessionHeartbeat";

vi.mock("@/lib/api/auth", () => ({
  heartbeat: vi.fn().mockResolvedValue({ expira_en_seg: 1800 }),
}));

import { heartbeat } from "@/lib/api/auth";

describe("SessionHeartbeat (T52, RF-8)", () => {
  let now = 0;

  beforeEach(() => {
    now = 0;
    vi.mocked(heartbeat).mockClear();
    vi.spyOn(Date, "now").mockImplementation(() => now);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("sends a heartbeat on the first activity event", () => {
    render(<SessionHeartbeat />);
    window.dispatchEvent(new Event("mousemove"));
    expect(heartbeat).toHaveBeenCalledTimes(1);
  });

  it("throttles subsequent events within the same minute", () => {
    render(<SessionHeartbeat />);
    window.dispatchEvent(new Event("click"));
    now += 30_000;
    window.dispatchEvent(new Event("keydown"));
    expect(heartbeat).toHaveBeenCalledTimes(1);
  });

  it("sends another heartbeat once a full minute has passed", () => {
    render(<SessionHeartbeat />);
    window.dispatchEvent(new Event("scroll"));
    now += 60_000;
    window.dispatchEvent(new Event("touchstart"));
    expect(heartbeat).toHaveBeenCalledTimes(2);
  });

  it("reacts to all five specified event types", () => {
    const events = ["mousemove", "click", "keydown", "scroll", "touchstart"];
    render(<SessionHeartbeat />);
    events.forEach((eventName, index) => {
      now = index * 60_000;
      window.dispatchEvent(new Event(eventName));
    });
    expect(heartbeat).toHaveBeenCalledTimes(events.length);
  });

  it("stops listening once unmounted", () => {
    const { unmount } = render(<SessionHeartbeat />);
    window.dispatchEvent(new Event("click"));
    expect(heartbeat).toHaveBeenCalledTimes(1);

    unmount();
    now += 60_000;
    window.dispatchEvent(new Event("click"));
    expect(heartbeat).toHaveBeenCalledTimes(1);
  });

  it("renders nothing visible", () => {
    const { container } = render(<SessionHeartbeat />);
    expect(container).toBeEmptyDOMElement();
  });
});
