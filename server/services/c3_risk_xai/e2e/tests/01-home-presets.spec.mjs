// Home screen, connection status and the three example presets.
import { expect, test } from '@playwright/test';
import { button, openApp, runPreset, text, watchConsole, expectNoBannedText, see, notSee } from '../support/app.mjs';
import { startC3, stopC3 } from '../support/servers.mjs';

test('home loads with connection status, start button, past checks and 3 examples', async ({ page }) => {
  const consoleWatch = watchConsole(page);
  await openApp(page);
  await see(page, 'Connected');
  await expect(button(page, 'Start a health check')).toBeVisible();
  await expect(button(page, 'Past checks (0)')).toBeVisible();
  for (const name of ['Higher-risk example', 'Lower-risk example', 'Missing details example']) {
    await expect(button(page, name)).toBeVisible();
  }
  await expect(button(page, 'Open connection settings')).toBeVisible();
  await expectNoBannedText(page, 'home');
  consoleWatch.check();
});

test('Check again: server stopped shows the offline note, restored shows Connected', async ({ page }) => {
  await openApp(page);
  await see(page, 'Connected');
  await stopC3();
  try {
    await button(page, 'Tap to check again').click();
    await see(page, 'Can’t connect right now.');
    await see(page, 'Not connected');
  } finally {
    await startC3();
  }
  await button(page, 'Check again').first().click();
  await see(page, 'Connected');
  await notSee(page, 'Can’t connect right now.');
});

test('Higher-risk example: High band, score ring and doctor referral', async ({ page }) => {
  const consoleWatch = watchConsole(page);
  await openApp(page);
  await runPreset(page, 'Higher-risk example');
  await see(page, 'Estimated risk: High');
  await see(page, /Your health score \d+ out of 100/);
  await see(page, 'Please see your doctor.');
  await see(page, 'Estimate for self-care support. Not medical advice.');
  await expectNoBannedText(page, 'result High');
  consoleWatch.check();
});

test('Lower-risk example: Low band and no referral', async ({ page }) => {
  await openApp(page);
  await runPreset(page, 'Lower-risk example');
  await see(page, 'Estimated risk: Low');
  await notSee(page, 'Please see your doctor.');
  await expectNoBannedText(page, 'result Low');
});

test('Missing details example: asks for more answers and shows no band', async ({ page }) => {
  await openApp(page);
  await button(page, 'Missing details example').click();
  await see(page, 'We need a few more answers', { timeout: 30_000 });
  await see(page, 'height and weight (BMI)');
  await notSee(page, 'estimated risk');
  await notSee(page, /out of 100/);
  await expectNoBannedText(page, 'insufficient');
});
