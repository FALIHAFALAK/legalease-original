import { expect, test } from '@playwright/test';
import { hasNoHorizontalOverflow } from './helpers';

const PUBLIC_PAGES = [
  { path: '/', name: 'homepage' },
  { path: '/how-it-works', name: 'how-it-works' },
  { path: '/pricing', name: 'pricing' },
  { path: '/templates', name: 'templates' },
  { path: '/about', name: 'about' },
  { path: '/contact', name: 'contact' },
  { path: '/login', name: 'login' },
  { path: '/register', name: 'register' },
];

test.describe('layout integrity', () => {
  for (const page of PUBLIC_PAGES) {
    test(`${page.name} renders without horizontal overflow`, async ({ page: p }) => {
      const response = await p.goto(page.path);
      expect(response?.status(), `${page.path} returned an error status`).toBeLessThan(400);
      await p.waitForLoadState('networkidle');
      const overflow = await hasNoHorizontalOverflow(p);
      expect(overflow.ok, `${page.path} overflows: ${overflow.detail}`).toBe(true);
    });
  }

  test('homepage has one h1 and a real document title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/LegalEase/);
    await expect(page.locator('h1')).toHaveCount(1);
  });

  test('primary navigation links resolve', async ({ page }) => {
    await page.goto('/');
    const header = page.locator('header');
    await expect(header).toBeVisible();

    const links = await header.locator('a[href^="/"]').evaluateAll((nodes) =>
      nodes.map((n) => (n as HTMLAnchorElement).getAttribute('href') ?? ''),
    );
    expect(links.length).toBeGreaterThan(0);

    for (const href of Array.from(new Set(links)).slice(0, 6)) {
      const res = await page.request.get(href);
      expect(res.status(), `${href} responded ${res.status()}`).toBeLessThan(400);
    }
  });

  test('mobile exposes a menu control that opens navigation', async ({ page, isMobile }) => {
    test.skip(!isMobile, 'the collapsed menu button only exists below the md breakpoint');
    await page.goto('/');
    const toggle = page.getByRole('button', { name: /toggle navigation/i });
    await expect(toggle).toBeVisible();
    await toggle.click();
    // The drawer exposes the section links that the desktop header hides.
    const drawer = page.getByRole('link', { name: 'Templates', exact: true });
    await expect(drawer).toBeVisible();
    await drawer.click();
    await expect(page).toHaveURL(/\/templates/);
  });

  test('hero call to action is clickable and reaches registration', async ({ page }) => {
    await page.goto('/');
    const cta = page.locator('a[href="/register"]:visible').first();
    await expect(cta).toBeVisible();
    await cta.click();
    await expect(page).toHaveURL(/\/register/);
  });
});
