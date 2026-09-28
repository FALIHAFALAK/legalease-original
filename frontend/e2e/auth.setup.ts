import { test as setup, expect } from '@playwright/test';
import path from 'node:path';
import { E2E_EMAIL, E2E_PASSWORD } from './helpers';

export const AUTH_FILE = path.join(__dirname, '.auth', 'user.json');

/**
 * Registers one shared account and persists its cookies.
 *
 * The backend rate-limits registration to 5 per hour per client (`require_csrf` +
 * `rate_limiter.check(client_key(request, "register"), 5, 3600)`), so authenticating once
 * and reusing the session keeps the suite runnable. If the account already exists we log in
 * instead, which makes repeat local runs work without wiping the database.
 */
setup('authenticate a shared test user', async ({ page, baseURL }) => {
  const email = process.env.E2E_EMAIL ?? E2E_EMAIL;
  const password = process.env.E2E_PASSWORD ?? E2E_PASSWORD;

  await page.goto(`${baseURL}/register`);
  await page.locator('#full_name').fill('E2E Reviewer');
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(password);

  const registerResponse = page.waitForResponse(
    (r) => r.url().includes('/api/auth/register'),
    { timeout: 30_000 },
  );
  await page.locator('button[type="submit"]').first().click();
  const registered = await registerResponse;

  if (registered.status() >= 400) {
    // 409 = already registered, 429 = rate limited. Fall back to logging in.
    await page.goto(`${baseURL}/login`);
    await page.locator('#email').fill(email);
    await page.locator('#password').fill(password);
    const loginResponse = page.waitForResponse((r) => r.url().includes('/api/auth/login'), {
      timeout: 30_000,
    });
    await page.locator('button[type="submit"]').first().click();
    const loggedIn = await loginResponse;
    expect(
      loggedIn.ok(),
      `could not authenticate ${email}: register=${registered.status()} login=${loggedIn.status()}`,
    ).toBe(true);
  }

  await page.context().storageState({ path: AUTH_FILE });
});
