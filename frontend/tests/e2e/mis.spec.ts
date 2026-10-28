import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = "e2e.superadmin@jatayues.com";
const MEMBER_EMAIL = "e2e.member@jatayues.com";
const FORCED_EMAIL = "e2e.forced@jatayues.com";
const E2E_PASSWORD = "E2e!Passw0rd2026";
const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000";

async function signIn(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Office People ID").fill(email);
  await page.locator("#password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test.describe("authenticated MIS workspace", () => {
  test("super admin signs in and sees the dashboard shell", async ({ page }) => {
    await signIn(page, ADMIN_EMAIL);

    await expect(
      page.getByRole("heading", { level: 1, name: /Good to see you/ }),
    ).toBeVisible();
    await expect(
      page
        .locator("footer:visible")
        .filter({ hasText: "Made and managed by JES Electronics Systems Pvt Ltd" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
    // The dashboard is client-rendered; it must not trigger an instant-navigation
    // validation error in the dev overlay.
    await expect(page.getByText(/could not validate that a segment/i)).toHaveCount(0);
  });

  test("super admin can reach every management section", async ({ page }) => {
    await signIn(page, ADMIN_EMAIL);

    for (const [link, heading] of [
      ["Projects", "Projects"],
      ["Inventory", "Inventory"],
      ["Purchase requests", "Purchase requests"],
      ["Alerts", "Alerts"],
      ["Users", "Users"],
      ["Time Counter", "Time Counter"],
      ["Audit trail", "Audit trail"],
    ] as const) {
      await page.getByRole("link", { name: link, exact: true }).click();
      await expect(
        page.getByRole("heading", { name: heading, level: 1 }),
      ).toBeVisible();
      await page.waitForLoadState("networkidle");
      await expect(page.getByText(/Unable to load/)).toHaveCount(0);
    }
  });

  test("super admin creates a project through the UI", async ({ page }) => {
    await signIn(page, ADMIN_EMAIL);
    const projectName = `E2E Playwright ${Date.now()}`;

    await page.goto("/projects/new");
    await page.getByLabel("Project name").fill(projectName);
    await page
      .getByLabel("Description")
      .fill("Created by the automated Playwright suite.");

    const person = page.locator("#member-0");
    await expect(person.locator("option")).not.toHaveCount(1);
    await person.selectOption({ index: 1 });

    await page.getByRole("button", { name: "Create project" }).click();

    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/, {
      timeout: 30_000,
    });
    await expect(
      page.getByRole("heading", { name: projectName, level: 1 }),
    ).toBeVisible();
    await expect(
      page.getByText("Ready for production", { exact: true }).first(),
    ).toBeVisible();
  });

  test("first-time users must replace their temporary password", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.getByLabel("Office People ID").fill(FORCED_EMAIL);
    await page.locator("#password").fill(E2E_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/change-password$/);
    await expect(
      page.getByRole("heading", { name: "Set a new password" }),
    ).toBeVisible();
    await expect(
      page.getByText("Your temporary password must be changed before you can use the MIS."),
    ).toBeVisible();

    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/change-password$/);
  });

  test("standard users cannot reach the user administration area", async ({
    page,
  }) => {
    await signIn(page, MEMBER_EMAIL);

    await expect(
      page.getByRole("link", { name: "Users", exact: true }),
    ).toHaveCount(0);

    await page.goto("/users");
    await expect(
      page.getByRole("heading", { name: "Access restricted" }),
    ).toBeVisible();
    await expect(page.getByText("Back to dashboard")).toBeVisible();
  });

  test("a shortage flows through purchase, delivery, and alerts", async ({
    page,
  }) => {
    await signIn(page, ADMIN_EMAIL);

    const stamp = Date.now();
    const sku = `E2E-UI-${stamp}`;
    const projectName = `E2E UI Flow ${stamp}`;

    const meResponse = await page.request.get(`${API_URL}/api/v1/auth/me`);
    expect(meResponse.status()).toBe(200);
    const me = (await meResponse.json()) as { id: string };

    // Seed a project whose BOM cannot be covered by the 2 units on hand.
    const itemResponse = await page.request.post(`${API_URL}/api/v1/inventory`, {
      data: {
        name: `E2E UI Widget ${stamp}`,
        sku,
        quantity_available: 2,
      },
    });
    expect(itemResponse.status()).toBe(201);
    const item = (await itemResponse.json()) as { id: string };

    const endDate = new Date();
    endDate.setDate(endDate.getDate() + 2);
    const projectResponse = await page.request.post(`${API_URL}/api/v1/projects`, {
      data: {
        name: projectName,
        description: "Created by the Playwright shortage workflow test.",
        type: "PRODUCTION",
        priority: "HIGH",
        start_date: new Date().toISOString().slice(0, 10),
        end_date: endDate.toISOString().slice(0, 10),
        members: [{ user_id: me.id, role_in_project: "DEVELOPER" }],
        bom: [{ item_id: item.id, quantity_required: 5 }],
      },
    });
    expect(projectResponse.status()).toBe(201);
    const project = (await projectResponse.json()) as {
      id: string;
      status: string;
    };
    expect(project.status).toBe("PENDING_INVENTORY");

    // The shortage is raised from the project page in one click.
    await page.goto(`/projects/${project.id}`);
    await expect(
      page.getByRole("heading", { name: projectName, level: 1 }),
    ).toBeVisible();
    await expect(
      page.getByText("Pending inventory", { exact: true }).first(),
    ).toBeVisible();
    await page.getByRole("button", { name: "Request 3", exact: true }).click();
    await expect(
      page.getByText("Purchase request raised for the full remaining shortage"),
    ).toBeVisible();
    await expect(page.getByText("3 requested", { exact: true })).toBeVisible();

    // Approve, order, and receive it from the procurement queue.
    await page.goto("/purchases");
    const row = page.locator("tr").filter({ hasText: sku });
    await expect(row).toBeVisible();

    await row.getByRole("button", { name: "Approve", exact: true }).click();
    await page.getByRole("button", { name: "Approve request" }).click();
    await expect(row.getByText("Approved", { exact: true })).toBeVisible();

    await row.getByRole("button", { name: "Mark ordered" }).click();
    await page.getByLabel("Delay reason").fill("Supplier lead time confirmed");
    await page.getByRole("button", { name: "Confirm order" }).click();
    await expect(row.getByText("Ordered", { exact: true })).toBeVisible();

    await row.getByRole("button", { name: "Mark delivered" }).click();
    await page.getByRole("button", { name: "Confirm delivery" }).click();
    await expect(row.getByText("Delivered", { exact: true })).toBeVisible();

    // Delivery allocates the stock and releases the project for production.
    await page.goto(`/projects/${project.id}`);
    await expect(
      page.getByText("Ready for production", { exact: true }).first(),
    ).toBeVisible();
    await expect(page.getByText("Every required item is fully allocated.")).toBeVisible();

    // The deadline window now produces a standard Time Counter alert.
    await page.goto("/settings");
    await page.getByRole("button", { name: "Run check now" }).click();
    await expect(page.getByText(/created 1 alerts/)).toBeVisible();

    await page.goto("/alerts");
    await expect(
      page.getByRole("link", { name: new RegExp(projectName) }),
    ).toBeVisible();
    await expect(page.getByText(/deadline is in 2 day/).first()).toBeVisible();
    await expect(page.getByText("Standard", { exact: true }).first()).toBeVisible();
  });
});
