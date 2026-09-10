import { describe, it, expect } from "vitest";
import { fetchWithMutex, getInflightCount } from "../utils/fetch-mutex.js";

describe("Fetch Mutex", () => {
  it("returns the same promise for concurrent calls with same key", async () => {
    let callCount = 0;
    const fetcher = async () => {
      callCount++;
      await new Promise((r) => setTimeout(r, 50));
      return { data: "test" };
    };

    const [result1, result2, result3] = await Promise.all([
      fetchWithMutex("key1", fetcher),
      fetchWithMutex("key1", fetcher),
      fetchWithMutex("key1", fetcher),
    ]);

    expect(callCount).toBe(1); // Only one actual fetch
    expect(result1).toEqual({ data: "test" });
    expect(result2).toEqual({ data: "test" });
    expect(result3).toEqual({ data: "test" });
  });

  it("allows different keys to fetch concurrently", async () => {
    let callCount = 0;
    const fetcher = async () => {
      callCount++;
      await new Promise((r) => setTimeout(r, 10));
      return { data: "test" };
    };

    await Promise.all([
      fetchWithMutex("keyA", fetcher),
      fetchWithMutex("keyB", fetcher),
    ]);

    expect(callCount).toBe(2);
  });

  it("cleans up after completion", async () => {
    const fetcher = async () => "done";

    await fetchWithMutex("cleanup-test", fetcher);
    expect(getInflightCount()).toBe(0);
  });

  it("cleans up after failure", async () => {
    const fetcher = async () => {
      throw new Error("fail");
    };

    try {
      await fetchWithMutex("fail-test", fetcher);
    } catch {
      // Expected
    }
    expect(getInflightCount()).toBe(0);
  });

  it("propagates errors to all waiters", async () => {
    const fetcher = async () => {
      throw new Error("shared error");
    };

    const [result1, result2] = await Promise.allSettled([
      fetchWithMutex("error-share", fetcher),
      fetchWithMutex("error-share", fetcher),
    ]);

    expect(result1.status).toBe("rejected");
    expect(result2.status).toBe("rejected");
  });
});
