import { expect, test } from '@playwright/test';
import { gotoDashboard, hasNoHorizontalOverflow } from './helpers';

const ORIGINAL = '../backend/tests/fixtures/website_development_agreement_original.txt';
const REVISED = '../backend/tests/fixtures/website_development_agreement_revised.txt';

test.describe('authenticated workspace', () => {
  test('dashboard renders for a signed-in user', async ({ page }) => {
    await gotoDashboard(page);
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Good to see you/i);

    // Stat cards and the documents list are the dashboard's core affordances.
    await expect(page.getByText('Total documents')).toBeVisible();
    await expect(page.getByRole('link', { name: /new document/i }).first()).toBeVisible();

    const overflow = await hasNoHorizontalOverflow(page);
    expect(overflow.ok, `dashboard overflows: ${overflow.detail}`).toBe(true);
  });

  test('document workspace shows the empty state before any upload', async ({ page }) => {
    await page.goto('/review');

    await expect(page.getByRole('heading', { name: /Review a document clause by clause/i })).toBeVisible();
    await expect(page.getByText('No review yet')).toBeVisible();
    await expect(page.getByRole('heading', { name: '1. Choose a file' })).toBeVisible();
    // The action must be unavailable until a file is chosen.
    await expect(page.getByRole('button', { name: /Review clauses/i })).toBeDisabled();

    const overflow = await hasNoHorizontalOverflow(page);
    expect(overflow.ok, `review empty state overflows: ${overflow.detail}`).toBe(true);
  });

  test('upload produces findings, clause viewer, and status controls', async ({ page }) => {
    await page.goto('/review');

    await page.locator('input[type="file"]').setInputFiles(ORIGINAL);
    await expect(page.getByText('website_development_agreement_original.txt')).toBeVisible();

    const submit = page.getByRole('button', { name: /Review clauses/i });
    await expect(submit).toBeEnabled();
    await submit.click();

    // Mock analysis is synchronous enough that the summary appears without extra polling.
    await expect(page.getByRole('heading', { name: /Findings \(/i })).toBeVisible({ timeout: 45_000 });

    // Clause viewer: native details/summary disclosure of extracted clauses.
    await expect(page.getByText(/clause[s]? extracted/).first()).toBeVisible();
    await expect(page.locator('details').first()).toBeVisible();

    // Finding card anatomy: severity badge, citation, and the flagged clause text.
    const firstFinding = page.locator('article[id^="finding-"]').first();
    await expect(firstFinding).toBeVisible();
    await expect(firstFinding.locator('mark').first()).toBeVisible();

    // A first-time review has nothing to compare against, and must say so.
    await expect(page.getByText('No earlier version to compare')).toBeVisible();

    const overflow = await hasNoHorizontalOverflow(page);
    expect(overflow.ok, `findings overflow: ${overflow.detail}`).toBe(true);
  });

  test('a revised upload produces a populated comparison panel', async ({ page }) => {
    await page.goto('/review');

    await page.locator('input[type="file"]').setInputFiles(ORIGINAL);
    await page.getByRole('button', { name: /Review clauses/i }).click();
    await expect(page.getByRole('heading', { name: /Findings \(/i })).toBeVisible({ timeout: 45_000 });

    // Start a fresh comparison pass seeded with the review we just produced.
    await page.getByRole('button', { name: /Compare a revised copy/i }).click();
    await page.locator('input[type="file"]').setInputFiles(REVISED);
    await page.getByRole('button', { name: /Review clauses/i }).click();

    await expect(page.getByRole('heading', { name: /Compared with/i })).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/addressed/i).first()).toBeVisible();
    await expect(page.getByText(/outstanding/i).first()).toBeVisible();

    const overflow = await hasNoHorizontalOverflow(page);
    expect(overflow.ok, `comparison panel overflows: ${overflow.detail}`).toBe(true);
  });

  test('app shell navigation moves between workspace sections', async ({ page, viewport }) => {
    await gotoDashboard(page);

    // The app shell collapses to a drawer below Tailwind's `lg` breakpoint (1024px), which
    // covers both phones and tablets in portrait. `isMobile` is not the right signal because
    // the tablet project emulates a desktop browser.
    const width = viewport?.width ?? 1440;
    const needsDrawer = width < 1024;
    const openDrawer = async () => {
      if (needsDrawer) await page.getByRole('button', { name: /open menu/i }).click();
    };

    await openDrawer();
    await page.getByRole('link', { name: 'Document review' }).click();
    await expect(page).toHaveURL(/\/review/);
    await expect(page.getByRole('heading', { name: /Review a document clause by clause/i })).toBeVisible();

    await openDrawer();
    await page.getByRole('link', { name: 'AI assistant' }).click();
    await expect(page).toHaveURL(/\/assistant/);
  });
});
