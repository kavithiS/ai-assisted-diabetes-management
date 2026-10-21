// Edge cases: double taps, fast navigation, browser back, refresh, slow network, errors.
import { expect, test } from '@playwright/test';
import { button, enableSemantics, openApp, runPreset, savedCount, text, watchConsole, see, notSee, atHome } from '../support/app.mjs';

test('double-click on an example saves only one result', async ({ page }) => {
  const deviceId = await openApp(page);
  await button(page, 'Higher-risk example').dblclick();
  await see(page, 'Estimated risk: High', { timeout: 30_000 });
  await page.waitForTimeout(3000);
  expect(await savedCount(deviceId)).toBe(1);
});

test('rapid navigation between result screens causes no errors', async ({ page }) => {
  const consoleWatch = watchConsole(page);
  await openApp(page);
  await runPreset(page, 'Higher-risk example');
  // As fast as the screens appear: each tap waits only for its screen to show.
  for (let i = 0; i < 4; i += 1) {
    await button(page, 'Why this score').click();
    await see(page, 'What shaped this score');
    await button(page, 'Back').click();
    await see(page, 'Update health information');
    await button(page, 'What you can do').click();
    await see(page, 'A suggestion for you');
    await button(page, 'Back').click();
    await see(page, 'Update health information');
  }
  await see(page, 'Estimated risk: High');
  consoleWatch.check();
});

test('browser back from the result returns to home', async ({ page }) => {
  await openApp(page);
  await runPreset(page, 'Higher-risk example');
  await page.goBack();
  await atHome(page);
  await see(page, 'Check again');
});

test('refresh in the middle of the form reopens home cleanly', async ({ page }) => {
  const consoleWatch = watchConsole(page);
  await openApp(page);
  await button(page, 'Start a health check').click();
  await see(page, 'Your health details');
  await page.reload();
  await enableSemantics(page);
  await see(page, 'Connected');
  await expect(button(page, 'Start a health check')).toBeVisible();
  consoleWatch.check();
});

test('slow network (2 s delay): the preparing screen shows, then the result', async ({ page }) => {
  await openApp(page);
  await page.route('**/api/v1/risk/assess**', async (route) => {
    await new Promise((r) => setTimeout(r, 2000));
    await route.continue();
  });
  await button(page, 'Higher-risk example').click();
  await see(page, 'Preparing your estimate');
  await see(page, 'Estimated risk: High', { timeout: 30_000 });
});

for (const status of [500, 503]) {
  test(`server ${status}: friendly error with Retry, no technical text`, async ({ page }) => {
    await openApp(page);
    await page.route('**/api/v1/risk/assess**', (route) =>
      route.fulfill({ status, contentType: 'application/json', body: '{"detail":"Internal Server Error"}' }));
    await button(page, 'Higher-risk example').click();
    await see(page, 'We couldn’t finish this check.', { timeout: 30_000 });
    await expect(button(page, 'Retry')).toBeVisible();
    await notSee(page, 'Internal Server Error');
  });
}

test('narrow phone (320 px): no sideways scrolling on the main screens', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await openApp(page);
  const noSideScroll = async (where) => {
    const wide = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(wide, where).toBe(false);
  };
  await noSideScroll('home');
  await runPreset(page, 'Higher-risk example');
  await noSideScroll('result');
  await page.screenshot({ path: test.info().outputPath('result-320.png') });
});
