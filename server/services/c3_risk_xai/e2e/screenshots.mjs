// Phone-size screenshots of each C3 screen for the PP1 slides.
//
// Needs a Flutter web build of the screenshot harness served at BASE_URL (default
// http://127.0.0.1:5191) and a running gateway. Uses the installed Chrome (no download).
//   node screenshots.mjs [outDir]
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { chromium } from '@playwright/test';

const base = process.env.BASE_URL ?? 'http://127.0.0.1:5191';
const outDir = process.argv[2] ?? '../docs/pp1/screens';
const screens = [
  ['01-home', 'home'],
  ['02-health-check', 'input'],
  ['03-result', 'result'],
  ['04-why-this-score', 'xai'],
  ['05-what-you-can-do', 'recs'],
  ['06-try-a-change', 'whatif'],
  ['07-past-checks', 'history'],
  ['08-settings', 'settings'],
  ['09-home-after-check', 'home2'],
];

const browser = await chromium.launch({ channel: 'chrome', args: ['--disable-web-security'] });
try {
  for (const scheme of ['light', 'dark']) {
    const dir = scheme === 'light' ? outDir : join(outDir, 'dark');
    await mkdir(dir, { recursive: true });
    for (const [name, screen] of screens) {
      const context = await browser.newContext({
        viewport: { width: 412, height: 915 },
        deviceScaleFactor: 2,
        colorScheme: scheme,
      });
      const page = await context.newPage();
      const errors = [];
      page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
      await page.goto(`${base}/?screen=${screen}&dark=${scheme === 'dark' ? 1 : 0}`);
      await page.waitForSelector('flutter-view, flt-glass-pane', { timeout: 30000 });
      // Server answer, page transition and the score count-up all finish well within this.
      await page.waitForTimeout(6000);
      await page.screenshot({ path: join(dir, `${name}.png`) });
      console.log(`${scheme} ${name}${errors.length ? `  console errors: ${errors.join(' | ')}` : ''}`);
      await context.close();
    }
  }
} finally {
  await browser.close();
}
