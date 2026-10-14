import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";

const tokenKey = "brasaland.access_token";
const password = "Auth02-test-password";
const root = path.resolve(__dirname, "../../..");
const email = () => `auth02-${crypto.randomUUID()}@example.com`;

async function seedSession(page: Page) {
  const userEmail = email();
  const created = await page.request.post("/api/backend/users", {
    data: { email: userEmail, password, name: "Test Member", phone: "12345", address: "Test address" },
  });
  expect(created.status()).toBe(201);
  const response = await page.request.post("/api/backend/auth/login", { data: { email: userEmail, password } });
  expect(response.ok()).toBe(true);
  const { access_token: token } = await response.json();
  await page.addInitScript(({ key, value }) => {
    if (!sessionStorage.getItem("auth-test-seeded")) {
      localStorage.setItem(key, value);
      sessionStorage.setItem("auth-test-seeded", "true");
    }
  }, { key: tokenKey, value: token });
  return { userEmail, token };
}

async function mockTracker(page: Page, status = 200) {
  await page.route("**/tracker/api/v1/**", async route => {
    expect(route.request().headers().authorization).toMatch(/^Bearer .+/);
    await route.fulfill({ status, json: status === 401 ? { detail: "Session expired" } : { data: [], total: 0, page: 1, limit: 100 } });
  });
}

for (const route of ["/", "/candidates/new", "/candidates/example", "/candidates/example/edit", "/account/profile", "/backoffice/", "/backoffice/suppliers/"]) {
  for (const invalid of [false, true]) {
    test(`${route}: redirects with ${invalid ? "invalid" : "missing"} token`, async ({ page }) => {
      if (invalid) await page.addInitScript(key => {
        if (!sessionStorage.getItem("auth-test-seeded")) {
          localStorage.setItem(key, "invalid.jwt.token");
          sessionStorage.setItem("auth-test-seeded", "true");
        }
      }, tokenKey);
      let trackerRequests = 0;
      await page.route("**/tracker/api/v1/**", route => { trackerRequests++; return route.abort(); });
      await page.goto(route);
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.getByRole("heading", { name: "Log in", exact: true })).toBeVisible();
      expect(await page.evaluate(key => localStorage.getItem(key), tokenKey)).toBeNull();
      expect(trackerRequests).toBe(0);
    });
  }
}

for (const [name, viewport] of Object.entries({ desktop: { width: 1440, height: 1000 }, mobile: { width: 390, height: 844 } })) {
  test(`${name}: registration, profile persistence, logout, and login`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    await mockTracker(page);
    const userEmail = email();
    await page.goto("/register");
    await page.getByLabel("Email", { exact: true }).fill(userEmail);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByLabel("Name (optional)").fill("New Member");
    await page.getByLabel("Phone (optional)").fill("5550102");
    await page.getByLabel("Address (optional)").fill("Original address");
    await page.screenshot({ path: testInfo.outputPath(`register-${name}.png`), fullPage: true });
    await page.getByRole("button", { name: "Create account", exact: true }).click();
    await expect(page).toHaveURL("/");
    await expect(page.getByRole("heading", { name: "Talent Pipeline Tracker" })).toBeVisible();
    const token = await page.evaluate(key => localStorage.getItem(key), tokenKey);
    expect(token).toMatch(/^[^.]+\.[^.]+\.[^.]+$/);
    await page.getByRole("link", { name: "My profile" }).click();
    await expect(page.getByLabel("Email", { exact: true })).toHaveValue(userEmail);
    await expect(page.getByLabel("Name", { exact: true })).toHaveValue("New Member");
    await expect(page.getByLabel("Phone", { exact: true })).toHaveValue("5550102");
    await expect(page.getByLabel("Address", { exact: true })).toHaveValue("Original address");
    await page.getByLabel("Name", { exact: true }).fill("Updated Member");
    await page.getByLabel("Phone", { exact: true }).fill("5559999");
    await page.getByLabel("Address", { exact: true }).fill("Updated address");
    const saved = page.waitForResponse(response => response.url().endsWith("/profiles/me") && response.request().method() === "PUT");
    await page.getByRole("button", { name: "Save profile" }).click();
    expect((await saved).request().headers().authorization).toBe(`Bearer ${token}`);
    await expect(page.getByRole("status")).toHaveText("Profile saved.");
    await page.reload();
    await expect(page.getByLabel("Name", { exact: true })).toHaveValue("Updated Member");
    await expect(page.getByLabel("Phone", { exact: true })).toHaveValue("5559999");
    await expect(page.getByLabel("Address", { exact: true })).toHaveValue("Updated address");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await page.locator("nav button, main button").evaluateAll(buttons => buttons
      .filter(button => button.scrollWidth > button.clientWidth)
      .map(button => ({ text: button.textContent, width: button.clientWidth, content: button.scrollWidth })))).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`profile-${name}.png`), fullPage: true });
    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login$/);
    expect(await page.evaluate(key => localStorage.getItem(key), tokenKey)).toBeNull();
    await page.getByLabel("Email", { exact: true }).fill(userEmail);
    await page.getByLabel("Password", { exact: true }).fill("wrong-password");
    await page.getByRole("button", { name: "Log in", exact: true }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Log in", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Talent Pipeline Tracker" })).toBeVisible();
    expect(errors).toEqual([]);
  });
}

test("registration shows API field errors and duplicate email", async ({ page }) => {
  const { userEmail } = await seedSession(page);
  await page.goto("/register");
  await page.getByLabel("Email", { exact: true }).fill(userEmail);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.locator("#email-error")).toHaveText("Email is already registered.");
  await page.getByLabel("Email", { exact: true }).fill(email());
  await page.getByLabel("Password", { exact: true }).fill("x".repeat(8) + "\u{1f600}".repeat(20));
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.locator("#password-error")).toContainText("72 UTF-8 bytes");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.route("**/api/backend/users", route => route.fulfill({ status: 422, json: { detail: [{ loc: ["body", "phone"], msg: "Invalid phone" }] } }));
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.locator("#phone-error")).toHaveText("Invalid phone");
});

test("forgot-password always confirms and disables the submitted form", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("link", { name: "Forgot your password?" }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  let requestBody: { email: string } | undefined;
  await page.route("**/api/backend/auth/forgot-password", async route => {
    requestBody = route.request().postDataJSON();
    await route.fulfill({ status: 200, json: { message: "If that address is registered, you'll receive a reset link shortly." } });
  });
  await page.getByLabel("Email", { exact: true }).fill("recovery@example.com");
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByRole("status")).toHaveText("If that address is registered, you'll receive a reset link shortly.");
  await expect(page.getByRole("button", { name: "Request sent" })).toBeDisabled();
  expect(requestBody).toEqual({ email: "recovery@example.com" });
});

test("reset-password submits the query token and shows the login success notice", async ({ page }) => {
  let requestBody: { token: string; new_password: string } | undefined;
  await page.route("**/api/backend/auth/reset-password", async route => {
    requestBody = route.request().postDataJSON();
    await route.fulfill({ status: 200, json: { message: "Password has been reset." } });
  });
  await page.goto("/reset-password?token=one-time-reset-token");
  await page.getByLabel("New password", { exact: true }).fill("New-frontend-password");
  await page.getByLabel("Confirm new password", { exact: true }).fill("New-frontend-password");
  await page.getByRole("button", { name: "Reset password" }).click();
  await expect(page).toHaveURL(/\/login\?password-reset=success$/);
  await expect(page.getByRole("status")).toHaveText("Your password was reset. You can sign in with your new password.");
  expect(requestBody).toEqual({ token: "one-time-reset-token", new_password: "New-frontend-password" });
});

test("reset-password reports an invalid token and offers a new link", async ({ page }) => {
  await page.route("**/api/backend/auth/reset-password", route => route.fulfill({
    status: 400, json: { detail: "Invalid or expired reset token." },
  }));
  await page.goto("/reset-password?token=expired-token-value");
  await page.getByLabel("New password", { exact: true }).fill("New-frontend-password");
  await page.getByLabel("Confirm new password", { exact: true }).fill("New-frontend-password");
  await page.getByRole("button", { name: "Reset password" }).click();
  await expect(page.getByRole("alert")).toHaveText("Invalid or expired reset token.");
  await expect(page.getByRole("link", { name: "Request a new reset link" })).toHaveAttribute("href", "/forgot-password");
});

test("change-password validates confirmation before sending and reports success", async ({ page }) => {
  const { token } = await seedSession(page);
  let requestBody: { current_password: string; new_password: string } | undefined;
  await page.route("**/api/backend/auth/change-password", async route => {
    requestBody = route.request().postDataJSON();
    expect(route.request().headers().authorization).toBe(`Bearer ${token}`);
    await route.fulfill({ status: 200, json: { message: "Password has been changed." } });
  });
  await page.goto("/account/change-password");
  await expect(page.getByRole("link", { name: "Change password" })).toBeVisible();
  await page.getByLabel("Current password", { exact: true }).fill(password);
  await page.getByLabel("New password", { exact: true }).fill("Changed-frontend-password");
  await page.getByLabel("Confirm new password", { exact: true }).fill("Does-not-match");
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.locator("#confirm_password-error")).toHaveText("Passwords do not match.");
  expect(requestBody).toBeUndefined();
  await page.getByLabel("Confirm new password", { exact: true }).fill("Changed-frontend-password");
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByRole("status")).toHaveText("Password changed successfully.");
  expect(requestBody).toEqual({ current_password: password, new_password: "Changed-frontend-password" });
});

test("profile protected 401 ends the session", async ({ page }) => {
  await seedSession(page);
  await page.goto("/account/profile");
  await expect(page.getByLabel("Name", { exact: true })).toBeVisible();
  await page.route("**/api/backend/profiles/me", route => route.fulfill({ status: 401, json: { detail: "Session expired" } }));
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(key => localStorage.getItem(key), tokenKey)).toBeNull();
});

test("tracker 401 clears the session", async ({ page }) => {
  await seedSession(page);
  await mockTracker(page, 401);
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(key => localStorage.getItem(key), tokenKey)).toBeNull();
});

test("backoffice: real upload, export, suppliers, 401, and logout", async ({ page }) => {
  const { token } = await seedSession(page);
  await page.goto("/backoffice/");
  await expect(page.getByRole("heading", { name: "Incident analysis", exact: true })).toBeVisible();
  await page.getByLabel("Choose incident CSV").setInputFiles(path.join(root, "scripts/incidents-brasaland-demo.csv"));
  const analyzed = page.waitForResponse(response => response.url().endsWith("/api/incidents/analyze"));
  await page.getByRole("button", { name: "Analyze file" }).click();
  const response = await analyzed;
  expect(response.status()).toBe(200);
  expect(response.request().headers().authorization).toBe(`Bearer ${token}`);
  await expect(page.locator("#total-records")).toHaveText("100");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  expect((await download).suggestedFilename()).toBe("results.csv");
  await page.getByRole("link", { name: "Supplier directory" }).click();
  await expect(page.locator("#supplier-rows tr")).toHaveCount(15);
  await page.route("**/suppliers?*", route => route.fulfill({ status: 401, json: { detail: "Expired" } }));
  await page.getByRole("button", { name: "Refresh directory" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(key => localStorage.getItem(key), tokenKey)).toBeNull();
});

test("backoffice logout clears the token", async ({ page }) => {
  await seedSession(page);
  await page.goto("/backoffice/");
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(key => localStorage.getItem(key), tokenKey)).toBeNull();
});

test("auth forms cannot send credentials before hydration", async ({ page }) => {
  await page.route("**/_next/**/*.js", route => route.abort());
  await page.goto("/login");
  await expect(page.getByLabel("Email", { exact: true })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Log in", exact: true })).toBeDisabled();
  await expect(page.locator("form")).toHaveAttribute("method", "post");
});

test("public Milestone 1 files stay unchanged and render without a session", async ({ page }) => {
  for (const file of ["index.html", "application.html", "project-shell.html", "validation.js"]) {
    expect(readFileSync(path.join(root, file), "utf8")).toBe(execFileSync("git", ["show", `HEAD:${file}`], { cwd: root, encoding: "utf8" }));
  }
  await page.route("https://milestone1.test/", route => route.fulfill({ contentType: "text/html", body: readFileSync(path.join(root, "index.html"), "utf8") }));
  await page.goto("https://milestone1.test/");
  await expect(page).toHaveURL("https://milestone1.test/");
  await expect(page.locator("h1")).toBeVisible();
  expect(await page.evaluate(key => localStorage.getItem(key), tokenKey)).toBeNull();
});