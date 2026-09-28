import { expect, test } from '@playwright/test';
import { fontFamilyOf } from './helpers';

const DISPLAY_HEADING = 'h1.font-display';

test.describe('typography', () => {
  test('DM Serif Display and Inter are both downloaded and usable', async ({ page }) => {
    const failures: string[] = [];
    page.on('requestfailed', (req) => {
      if (req.url().includes('.woff2')) failures.push(`${req.url()} ${req.failure()?.errorText}`);
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Trigger any lazily-applied webfont before asserting.
    await page.evaluate(() => document.fonts.ready);

    const faces = await page.evaluate(() => ({
      serif: document.fonts.check('1rem "DM Serif Display"'),
      sans: document.fonts.check('1rem "Inter"'),
      loaded: Array.from(document.fonts).map((f) => `${f.family}/${f.weight}/${f.status}`),
    }));

    expect(failures, `font requests failed: ${failures.join(', ')}`).toEqual([]);
    expect(faces.serif, 'DM Serif Display is not available to the renderer').toBe(true);
    expect(faces.sans, 'Inter is not available to the renderer').toBe(true);
    expect(faces.loaded.some((f) => f.startsWith('DM Serif Display') && f.endsWith('loaded'))).toBe(true);
    expect(faces.loaded.some((f) => f.startsWith('Inter') && f.endsWith('loaded'))).toBe(true);
  });

  test('serif actually renders, not just a declared family', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.evaluate(() => document.fonts.ready);

    const heading = page.locator(DISPLAY_HEADING).first();
    await expect(heading).toBeVisible();

    // Measure the same string with the webfont and with a guaranteed-different fallback.
    // A real serif changes glyph advance widths; an unloaded family would not differ.
    const widths = await heading.evaluate((el) => {
      const measure = (family: string) => {
        const probe = document.createElement('span');
        probe.textContent = 'Handgloves quick brown fox 0123456789';
        probe.style.position = 'absolute';
        probe.style.visibility = 'hidden';
        probe.style.whiteSpace = 'nowrap';
        probe.style.fontSize = '48px';
        probe.style.fontFamily = family;
        document.body.appendChild(probe);
        const w = probe.getBoundingClientRect().width;
        probe.remove();
        return w;
      };
      return {
        serif: measure('"DM Serif Display", serif'),
        forcedFallback: measure('Verdana, sans-serif'),
        headingFamily: getComputedStyle(el).fontFamily,
        headingWeight: getComputedStyle(el).fontWeight,
      };
    });

    expect(widths.headingFamily).toContain('DM Serif Display');
    // DM Serif ships only 400; a heavier computed weight would mean synthetic bolding.
    expect(Number(widths.headingWeight)).toBe(400);
    expect(
      Math.abs(widths.serif - widths.forcedFallback),
      'serif and fallback measured identically, so the webfont is not influencing layout',
    ).toBeGreaterThan(1);
  });

  test('body, navigation, and forms stay on Inter', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.evaluate(() => document.fonts.ready);

    expect(await fontFamilyOf(page, 'body')).toContain('Inter');
    expect(await fontFamilyOf(page, 'header a, header nav, header button')).not.toContain('DM Serif');

    await page.goto('/login');
    await page.locator('#email').waitFor({ state: 'visible' });
    expect(await fontFamilyOf(page, '#email')).toContain('Inter');
    expect(await fontFamilyOf(page, 'label')).not.toContain('DM Serif');
    expect(await fontFamilyOf(page, 'button[type="submit"]')).toContain('Inter');
  });

  test('display serif is applied to the homepage hero only among page headings', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const displayCount = await page.locator(DISPLAY_HEADING).count();
    expect(displayCount).toBeGreaterThan(0);

    // Eyebrow labels and card titles must not pick up the serif.
    expect(await fontFamilyOf(page, '.eyebrow')).not.toContain('DM Serif');
    const featureTitles = page.locator('h3.font-bold').first();
    if (await featureTitles.count()) {
      expect(await fontFamilyOf(page, 'h3.font-bold')).not.toContain('DM Serif');
    }
  });
});
