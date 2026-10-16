import { ApiError, TOKEN_KEY, apiRequest, endSession, getToken, sessionFetch } from "../auth/session";

const storage = {
  getItem: jest.fn(),
  removeItem: jest.fn(),
};
const replace = jest.fn();
const fetchMock = jest.fn() as jest.MockedFunction<typeof fetch>;

beforeEach(() => {
  jest.resetAllMocks();
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { localStorage: storage, location: { replace } },
  });
  globalThis.fetch = fetchMock;
  storage.getItem.mockReturnValue("stored-token");
});

afterAll(() => {
  jest.restoreAllMocks();
});

describe("getToken", () => {
  test("reads the shared token key", () => {
    expect(getToken()).toBe("stored-token");
    expect(storage.getItem).toHaveBeenCalledWith(TOKEN_KEY);
  });

  test("returns null without a stored session", () => {
    storage.getItem.mockReturnValue(null);
    expect(getToken()).toBeNull();
  });

  test("does not invent a session when storage is inaccessible", () => {
    storage.getItem.mockImplementation(() => { throw new Error("storage blocked"); });
    expect(getToken).toThrow("storage blocked");
  });
});

describe("endSession", () => {
  test("removes credentials before navigating to login", () => {
    endSession();
    expect(storage.removeItem).toHaveBeenCalledWith(TOKEN_KEY);
    expect(replace).toHaveBeenCalledWith("/login");
    expect(storage.removeItem.mock.invocationCallOrder[0]).toBeLessThan(replace.mock.invocationCallOrder[0]);
  });

  test("does not report logout completion if cleanup fails", () => {
    storage.removeItem.mockImplementation(() => { throw new Error("storage blocked"); });
    expect(endSession).toThrow("storage blocked");
    expect(replace).not.toHaveBeenCalled();
  });
});

describe("sessionFetch", () => {
  test("uses the current token and preserves custom headers", async () => {
    const response = new Response("{}");
    fetchMock.mockResolvedValue(response);
    expect(await sessionFetch("/auth/me", { headers: { "X-Request-ID": "request-id" } })).toBe(response);
    const options = fetchMock.mock.calls[0][1]!;
    expect((options.headers as Headers).get("Authorization")).toBe("Bearer stored-token");
    expect((options.headers as Headers).get("X-Request-ID")).toBe("request-id");
    expect(options.cache).toBe("no-store");
  });

  test("sets JSON content type for a JSON body", async () => {
    fetchMock.mockResolvedValue(new Response("{}"));
    await sessionFetch("/auth/login", { method: "POST", body: "{}" }, false);
    expect((fetchMock.mock.calls[0][1]!.headers as Headers).get("Content-Type")).toBe("application/json");
    expect(storage.getItem).not.toHaveBeenCalled();
  });

  test("leaves multipart boundaries to fetch", async () => {
    fetchMock.mockResolvedValue(new Response("{}"));
    await sessionFetch("/upload", { method: "POST", body: new FormData() });
    expect((fetchMock.mock.calls[0][1]!.headers as Headers).has("Content-Type")).toBe(false);
  });

  test("missing token clears the session and prevents the request", async () => {
    storage.getItem.mockReturnValue(null);
    await expect(sessionFetch("/auth/me")).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(storage.removeItem).toHaveBeenCalledWith(TOKEN_KEY);
    expect(replace).toHaveBeenCalledWith("/login");
  });

  test("expired protected session is removed", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 401 }));
    await expect(sessionFetch("/auth/me")).rejects.toMatchObject({ status: 401, message: expect.stringContaining("expired") });
    expect(storage.removeItem).toHaveBeenCalledWith(TOKEN_KEY);
    expect(replace).toHaveBeenCalledWith("/login");
  });

  test("failed public login does not clear another session", async () => {
    const response = new Response(null, { status: 401 });
    fetchMock.mockResolvedValue(response);
    expect(await sessionFetch("/auth/login", {}, false)).toBe(response);
    expect(storage.removeItem).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
  });
});

describe("apiRequest", () => {
  test("returns successful application data", async () => {
    fetchMock.mockResolvedValue(Response.json({ id: "owner" }));
    await expect(apiRequest("/auth/me")).resolves.toEqual({ id: "owner" });
  });

  test("accepts successful commands with no returned data", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(apiRequest("/users/owner", { method: "DELETE" })).resolves.toBeUndefined();
  });

  test("network failure becomes a user-safe error", async () => {
    fetchMock.mockRejectedValue(new Error("private connection details"));
    await expect(apiRequest("/auth/me")).rejects.toMatchObject({
      status: 0, message: expect.stringContaining("Unable to connect"),
    });
  });

  test("preserves authentication errors", async () => {
    storage.getItem.mockReturnValue(null);
    await expect(apiRequest("/auth/me")).rejects.toMatchObject({ status: 401, message: "Please sign in to continue." });
  });

  test.each([
    [400, "process that request"], [401, "email or password"], [403, "permission"],
    [404, "find that information"], [409, "already exists"], [422, "highlighted fields"],
    [429, "Too many attempts"], [500, "temporarily unavailable"],
  ])("maps error %i without exposing private server details", async (status, message) => {
    fetchMock.mockResolvedValue(Response.json({ detail: "private database credentials" }, { status }));
    await expect(apiRequest("/auth/login", {}, false)).rejects.toMatchObject({ status, message: expect.stringContaining(message) });
  });

  test("duplicate email identifies the field to correct", async () => {
    fetchMock.mockResolvedValue(Response.json({}, { status: 409 }));
    await expect(apiRequest("/users", {}, false)).rejects.toMatchObject({
      fields: { email: "An account with this email already exists." },
    });
  });

  test("validation errors select valid field names and ignore malformed issues", async () => {
    fetchMock.mockResolvedValue(Response.json({ detail: [
      { loc: ["body", "password"], msg: "sensitive details" },
      null, "invalid", {}, { loc: "not-an-array" }, { loc: ["body", 0] },
    ] }, { status: 422 }));
    await expect(apiRequest("/users", {}, false)).rejects.toMatchObject({
      fields: { password: "Please check this field and try again." },
    });
  });

  test("non-JSON failures still produce safe application errors", async () => {
    fetchMock.mockResolvedValue(new Response("private upstream failure", { status: 503 }));
    await expect(apiRequest("/auth/me")).rejects.toMatchObject({ status: 503, fields: {} });
  });

  test("unreadable successful response is rejected", async () => {
    fetchMock.mockResolvedValue(new Response("not-json"));
    await expect(apiRequest("/auth/me")).rejects.toMatchObject({ status: 200, message: expect.stringContaining("unreadable") });
  });
});

test("ApiError retains status and field context", () => {
  const error = new ApiError("Invalid input", 422, { password: "Required" });
  expect(error).toBeInstanceOf(Error);
  expect(error.status).toBe(422);
  expect(error.fields).toEqual({ password: "Required" });
});