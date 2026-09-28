import { expect, type Page } from '@playwright/test';

/**
 * A single shared account for the suite. The domain must be a real, non-reserved one because
 * the backend validates addresses with `email-validator`, which rejects `.test`/`.example`.
 * No mail is sent: registration only creates the user and sets a session cookie.
 */
export const E2E_EMAIL = process.env.E2E_EMAIL ?? 'legalease.e2e@legalease-qa.dev';
export const E2E_PASSWORD = 'Str0ng-Passw0rd!test';

export function uniqueEmail(prefix = 'e2e'): string {
  return `${prefix}.${Date.now()}.${Math.floor(Math.random() * 1e6)}@legalease-qa.dev`;
}

/** Sends the browser to the dashboard, relying on the shared storageState for the session. */
export async function gotoDashboard(page: Page): Promise<void> {
  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible({ timeout: 30_000 });
}

export type Rgb = { r: number; g: number; b: number };

export function parseRgb(value: string): Rgb {
  const nums = value.match(/[\d.]+/g);
  if (!nums || nums.length < 3) throw new Error(`Unparseable colour: ${value}`);
  return { r: Number(nums[0]), g: Number(nums[1]), b: Number(nums[2]) };
}

function channel(value: number): number {
  const v = value / 255;
  return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance({ r, g, b }: Rgb): number {
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/** WCAG 2.1 contrast ratio between two opaque colours, 1..21. */
export function contrastRatio(a: Rgb, b: Rgb): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/**
 * Resolves the first non-transparent background colour walking up the ancestor chain, which is
 * what a reader actually perceives behind the text.
 */
export async function effectiveBackground(page: Page, selector: string): Promise<Rgb> {
  const raw = await page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    let node: Element | null = el;
    while (node) {
      const bg = getComputedStyle(node).backgroundColor;
      const alpha = bg.match(/[\d.]+/g);
      if (bg && bg !== 'transparent' && (!alpha || alpha.length < 4 || Number(alpha[3]) > 0.85)) {
        return bg;
      }
      node = node.parentElement;
    }
    return getComputedStyle(document.body).backgroundColor;
  }, selector);
  if (!raw) throw new Error(`No element for selector: ${selector}`);
  return parseRgb(raw);
}

export async function fontFamilyOf(page: Page, selector: string): Promise<string> {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    return el ? getComputedStyle(el).fontFamily : '';
  }, selector);
}

/** True when the document has no element wider than the viewport (no horizontal scroll). */
export async function hasNoHorizontalOverflow(page: Page): Promise<{ ok: boolean; detail: string }> {
  const result = await page.evaluate(() => {
    // Compare against `innerWidth`, not `clientWidth`: `clientWidth` excludes the vertical
    // scrollbar, so a page that simply scrolls vertically reports a false overflow of exactly
    // the scrollbar width.
    const docWidth = window.innerWidth;
    const scrollWidth = document.documentElement.scrollWidth;
    if (scrollWidth <= docWidth + 1) return { ok: true, detail: `${scrollWidth} <= ${docWidth}` };

    // An element only widens the page when no ancestor clips it, so skip clipped subtrees
    // and report the genuine offender instead of innocent decorative children.
    const isClipped = (el: Element) => {
      let node = el.parentElement;
      while (node && node !== document.documentElement) {
        if (/hidden|clip|auto|scroll/.test(getComputedStyle(node).overflowX)) return true;
        node = node.parentElement;
      }
      return false;
    };

    const offenders: string[] = [];
    document.querySelectorAll<HTMLElement>('body *').forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0 || rect.right <= docWidth + 1) return;
      const style = getComputedStyle(el);
      if (style.position === 'fixed' || style.visibility === 'hidden' || style.display === 'none') return;
      if (isClipped(el)) return;
      offenders.push(
        `${el.tagName.toLowerCase()}.${String(el.className).slice(0, 70)} right=${Math.round(rect.right)}`,
      );
    });
    return {
      ok: false,
      detail:
        `scrollWidth=${scrollWidth} clientWidth=${docWidth}; unclipped offenders: ` +
        (offenders.length ? offenders.slice(0, 4).join(' | ') : 'none (overflow may come from a margin or transform)'),
    };
  });
  return result;
}

export function projectName(): string {
  return process.env.PW_PROJECT ?? 'desktop';
}
