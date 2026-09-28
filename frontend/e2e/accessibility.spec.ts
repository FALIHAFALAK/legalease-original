import { expect, test } from '@playwright/test';
import { contrastRatio, effectiveBackground, fontFamilyOf, parseRgb } from './helpers';

/** Foreground/background pairs that carry meaning on the marketing and auth surfaces. */
const CONTRAST_TARGETS: { name: string; selector: string; min: number }[] = [
  { name: 'body copy', selector: 'main p', min: 4.5 },
  { name: 'muted supporting text', selector: '.text-muted', min: 4.5 },
  { name: 'primary link / accent text', selector: 'a[href="/how-it-works"]', min: 4.5 },
  { name: 'eyebrow label', selector: '.eyebrow', min: 4.5 },
  { name: 'footer text', selector: 'footer p', min: 4.5 },
];

test.describe('accessibility', () => {
  test('text contrast meets WCAG AA on the homepage', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const failures: string[] = [];
    for (const target of CONTRAST_TARGETS) {
      const locator = page.locator(target.selector).first();
      if ((await locator.count()) === 0) continue;
      if (!(await locator.isVisible())) continue;

      const colour = await locator.evaluate((el) => getComputedStyle(el).color);
      const bg = await effectiveBackground(page, target.selector);
      const ratio = contrastRatio(parseRgb(colour), bg);
      if (ratio < target.min) {
        failures.push(`${target.name}: ${ratio.toFixed(2)}:1 (needs ${target.min}:1) fg=${colour} bg=rgb(${bg.r}, ${bg.g}, ${bg.b})`);
      }
    }
    expect(failures, `Contrast failures:\n${failures.join('\n')}`).toEqual([]);
  });

  test('form controls meet AA and are labelled', async ({ page }) => {
    await page.goto('/register');
    await page.locator('#email').waitFor({ state: 'visible' });

    const unlabelled = await page.evaluate(() => {
      const bad: string[] = [];
      document.querySelectorAll<HTMLElement>('input, select, textarea').forEach((el) => {
        if ((el as HTMLInputElement).type === 'hidden') return;
        const id = el.getAttribute('id');
        const hasLabel = id ? !!document.querySelector(`label[for="${id}"]`) : false;
        const hasAria = !!el.getAttribute('aria-label') || !!el.getAttribute('aria-labelledby');
        const hasPlaceholder = !!el.getAttribute('placeholder');
        if (!hasLabel && !hasAria && !hasPlaceholder) bad.push(el.outerHTML.slice(0, 90));
      });
      return bad;
    });
    expect(unlabelled, `Unlabelled form controls:\n${unlabelled.join('\n')}`).toEqual([]);

    const bg = await effectiveBackground(page, '#email');
    const ratio = contrastRatio(parseRgb(await page.locator('#email').evaluate((el) => getComputedStyle(el).color)), bg);
    expect(ratio, `input text contrast ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(4.5);
  });

  test('page exposes a single h1, a main landmark, and a skip-friendly tab order', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toHaveCount(1);
    await expect(page.locator('main')).toHaveCount(1);

    // Tab from the top of the document and confirm focus lands on real interactive elements.
    const seen: string[] = [];
    for (let i = 0; i < 8; i += 1) {
      await page.keyboard.press('Tab');
      const info = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        if (!el || el === document.body) return null;
        return el.tagName.toLowerCase() + (el.getAttribute('href') ? `[${el.getAttribute('href')}]` : '');
      });
      if (info) seen.push(info);
    }
    expect(seen.length, 'Tab did not reach any interactive element').toBeGreaterThan(2);
    expect(seen.every((s) => ['a', 'button', 'input'].some((t) => s.startsWith(t)))).toBe(true);
  });

  test('focus is visibly indicated on keyboard navigation', async ({ page }) => {
    await page.goto('/');
    await page.keyboard.press('Tab');
    const outline = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el) return null;
      const s = getComputedStyle(el);
      return { width: s.outlineWidth, style: s.outlineStyle, shadow: s.boxShadow };
    });
    expect(outline, 'nothing was focused').not.toBeNull();
    const hasRing = outline!.style !== 'none' && parseFloat(outline!.width) > 0;
    const hasShadow = outline!.shadow !== 'none' && outline!.shadow !== '';
    expect(hasRing || hasShadow, `no visible focus indicator: ${JSON.stringify(outline)}`).toBe(true);
  });

  test('reduced motion disables transitions and looping animation', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const offenders = await page.evaluate(() => {
      const bad: string[] = [];
      document.querySelectorAll<HTMLElement>('body *').forEach((el) => {
        const s = getComputedStyle(el);
        const dur = parseFloat(s.transitionDuration) || 0;
        const animDur = parseFloat(s.animationDuration) || 0;
        const iter = s.animationIterationCount;
        if (dur > 0.05) bad.push(`${el.tagName.toLowerCase()}.${String(el.className).slice(0, 40)} transition=${s.transitionDuration}`);
        if (animDur > 0.05 && iter === 'infinite') bad.push(`${el.tagName.toLowerCase()}.${String(el.className).slice(0, 40)} animation=${s.animationDuration} infinite`);
      });
      return bad.slice(0, 6);
    });
    expect(offenders, `motion still active under prefers-reduced-motion:\n${offenders.join('\n')}`).toEqual([]);
  });

  test('serif is not used for dense reading surfaces', async ({ page }) => {
    await page.goto('/how-it-works');
    const body = await fontFamilyOf(page, 'main p');
    expect(body).toContain('Inter');
    expect(body).not.toContain('DM Serif');
  });

  test('images and icons carry accessible names or are hidden', async ({ page }) => {
    await page.goto('/');
    const bad = await page.evaluate(() => {
      const out: string[] = [];
      document.querySelectorAll('img').forEach((img) => {
        if (img.alt === null || img.alt === undefined) out.push(img.outerHTML.slice(0, 80));
      });
      document.querySelectorAll<HTMLElement>('button').forEach((b) => {
        const name = (b.getAttribute('aria-label') || b.textContent || '').trim();
        if (name === '') out.push(b.outerHTML.slice(0, 80));
      });
      return out;
    });
    expect(bad, `elements without accessible names:\n${bad.join('\n')}`).toEqual([]);
  });
});
