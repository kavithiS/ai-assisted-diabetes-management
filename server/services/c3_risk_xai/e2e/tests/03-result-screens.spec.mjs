// Analysis, result, Why this score, What you can do, Try a change: every button, and no
// banned word or raw number on any of them (visible text and screen-reader labels).
import { expect, test } from '@playwright/test';
import {
  button, expectNoBannedText, openApp, runPreset, savedCount, scrollTo, text, watchConsole, see, notSee, atHome, back, example, goHome } from '../support/app.mjs';

test('analysis: a forced failure shows Retry, and Retry gives the result', async ({ page }) => {
  await openApp(page);
  let failed = false;
  await page.route('**/api/v1/risk/assess**', (route) => {
    if (!failed) {
      failed = true;
      return route.abort('connectionrefused');
    }
    return route.continue();
  });
  await (await example(page, 'Higher-risk example')).click();
  await see(page, 'We couldn’t finish this check.', { timeout: 30_000 });
  await button(page, 'Retry').click();
  await see(page, 'Estimated risk: High', { timeout: 30_000 });
});

test('result: Why this score, What you can do, Update health information and Back all work', async ({ page }) => {
  const consoleWatch = watchConsole(page);
  await openApp(page);
  await runPreset(page, 'Higher-risk example');

  await button(page, 'Why this score').click();
  await see(page, 'What shaped this score');
  await see(page, 'May raise your estimate');
  await see(page, 'Main reasons:');
  await expectNoBannedText(page, 'Why this score');
  await back(page);

  await button(page, 'What you can do').click();
  await see(page, 'A suggestion for you');
  await see(page, 'Try this first');
  const recs = await page.evaluate(() => document.querySelector('flt-semantics-host')?.textContent ?? '');
  expect(recs).not.toMatch(/(increase|reduce|stop|change|double|skip) (your |the )?(dose|medicine|medication|insulin|tablets)/i);
  await expectNoBannedText(page, 'What you can do');
  await back(page);

  await button(page, 'Update health information').click();
  await see(page, 'Your health details');
  // The previous answers are carried over (the web input reports no value until focused,
  // so the BMI line, worked out from those answers, is the visible proof).
  await see(page, 'Your BMI: 27.8');
  await expectNoBannedText(page, 'health check form');
  // Back from the form returns to the result; Back again goes home.
  await button(page, 'Back').click();
  await expect(button(page, 'Update health information')).toBeVisible();
  await goHome(page);

  // Home now shows the score card.
  await see(page, /Your health score \d+ out of 100/);
  await expect(page.getByRole('button', { name: 'Check again', exact: true })).toBeVisible();
  consoleWatch.check();
});

test('What you can do: the Try a change button opens the preview', async ({ page }) => {
  await openApp(page);
  await runPreset(page, 'Higher-risk example');
  await button(page, 'What you can do').click();
  const go = await scrollTo(page, button(page, 'Try a change'));
  await go.click();
  await see(page, 'Explore how a different answer could change your score.');
});

test('Try a change: each option gives a new estimate, and nothing is saved', async ({ page }) => {
  const deviceId = await openApp(page);
  await runPreset(page, 'Higher-risk example');
  await expect.poll(() => savedCount(deviceId)).toBe(1);
  await button(page, 'What you can do').click();
  await (await scrollTo(page, button(page, 'Try a change'))).click();
  await see(page, 'Preview only. This check is not saved.');

  // Expected scores come from the server for the Higher-risk answers (measured with
  // direct API calls): activity low/moderate/high = 58/63/68 with borderline-high
  // cholesterol; with high activity, cholesterol normal/high = 71/65.
  await see(page, /Estimated health score\s*58\b/);
  const steps = [
    ['Moderate', 0, 63],
    ['High', 0, 68],
    ['Normal', 0, 71],
    ['High', 1, 65],
  ];
  for (const [option, index, expected] of steps) {
    await page.getByRole('checkbox', { name: option, exact: true }).nth(index).click();
    await button(page, 'Update estimate').click();
    await see(page, new RegExp(`58\\s*→\\s*${expected}\\b`));
  }
  expect(await savedCount(deviceId), 'previews must not be saved').toBe(1);
  await expectNoBannedText(page, 'Try a change');
});

// The hidden long-press Details view is checked by the Flutter widget test "long-pressing
// the result title opens Details without raw probability" (mouse long-press through the
// web build is not reliable enough for a browser test).
