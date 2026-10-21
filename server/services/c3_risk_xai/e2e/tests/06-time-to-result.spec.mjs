// Time to first result, measured like a user sees it: click an example -> band on screen.
// 5 runs, median reported honestly against the 2 s target (NFR1). Saved to
// results/latency_e2e.json. Phone size only (one browser is enough for timing).
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { test } from '@playwright/test';
import { openApp, see, example } from '../support/app.mjs';
import { e2eDir } from '../support/servers.mjs';

test('median time to first result over 5 runs', async ({ page }, info) => {
  test.skip(info.project.name !== 'phone', 'measured once, at phone size');
  const runs = [];
  for (let i = 0; i < 5; i += 1) {
    await openApp(page);
    await see(page, 'Connected');
    const higher = await example(page, 'Higher-risk example'); // opened before the clock starts
    const started = Date.now();
    await higher.click();
    // Checked every 50 ms in the page itself, so the timing is not rounded up.
    await page.waitForFunction(
      () => [...document.querySelectorAll('flt-semantics-host *')].some((e) =>
        (e.getAttribute('aria-label') ?? '').includes('Estimated risk: High')
        || e.textContent.includes('Estimated risk: High')),
      null,
      { polling: 50, timeout: 30_000 },
    );
    runs.push((Date.now() - started) / 1000);
  }
  const sorted = [...runs].sort((a, b) => a - b);
  const median = sorted[2];
  const result = {
    what: 'Browser time from clicking the Higher-risk example to the band on screen',
    where: 'Flutter web release build in Chrome, gateway 8010 -> C3 8013 on this laptop',
    runs_seconds: runs,
    median_seconds: median,
    target_seconds: 2,
    meets_target: median <= 2,
    measured_at: new Date().toISOString(),
  };
  mkdirSync(join(e2eDir, 'results'), { recursive: true });
  writeFileSync(join(e2eDir, 'results', 'latency_e2e.json'), `${JSON.stringify(result, null, 2)}\n`);
  console.log(`time to first result: runs=${runs.join(', ')} s, median=${median} s`);
});
