// Past checks, Settings, delete my results and the audit log.
import { expect, test } from '@playwright/test';
import {
  auditRows, button, expectNoBannedText, openApp, runPreset, savedCount, text, see, notSee, atHome } from '../support/app.mjs';
import { tap } from '../support/app.mjs';
import { gatewayUrl, restartC3 } from '../support/servers.mjs';

async function home(page) {
  await button(page, 'Back').click();
  await atHome(page);
}

test('Past checks: empty first, then lists server results and opens an old one', async ({ page }) => {
  await openApp(page);
  await button(page, 'Past checks (0)').click();
  await see(page, 'No saved results yet.');
  await home(page);

  await runPreset(page, 'Higher-risk example');
  await home(page);
  await runPreset(page, 'Lower-risk example');
  await home(page);
  await tap(page, 'Past checks');
  await see(page, 'Saved checks');
  await see(page, 'Estimated risk: High');
  await see(page, 'Estimated risk: Low');
  await expectNoBannedText(page, 'Past checks');

  await button(page, 'Estimated risk: High').click();
  await see(page, 'Saved check');
  await see(page, 'Estimated risk: High');
});

test('Past checks: database stopped shows the offline note and this session', async ({ page }) => {
  test.setTimeout(240_000);
  await restartC3({ databaseDown: true });
  try {
    await openApp(page);
    await runPreset(page, 'Higher-risk example');
    await see(page, 'This check wasn’t saved.');
    await home(page);
    await tap(page, 'Past checks');
    await see(page, 'Past checks are offline right now.');
    await see(page, 'Estimated risk: High');
  } finally {
    await restartC3();
  }
});

test('Settings: delete my saved results empties Past checks; audit keeps no health answers', async ({ page }) => {
  const deviceId = await openApp(page);
  await runPreset(page, 'Higher-risk example');
  await home(page);
  await runPreset(page, 'Lower-risk example');
  await home(page);
  await expect.poll(() => savedCount(deviceId)).toBe(2);

  await tap(page, 'Open connection settings');
  await see(page, 'Settings');
  await expectNoBannedText(page, 'Settings');
  await button(page, 'Delete my saved results').click();
  await see(page, 'This cannot be undone.');
  await page.getByRole('button', { name: 'Delete', exact: true }).click();
  await see(page, 'Deleted 2 saved results.');
  expect(await savedCount(deviceId)).toBe(0);
  await home(page);
  await tap(page, 'Past checks');
  await see(page, 'No saved results yet.');

  const audit = auditRows(deviceId);
  expect(audit.columns.sort()).toEqual(['action', 'created_at', 'detail', 'device_id', 'id']);
  const actions = audit.rows.map((r) => r.action);
  expect(actions).toContain('assess');
  expect(actions).toContain('delete_device_records');
  for (const row of audit.rows) {
    // Only a status word or a count: never answers, scores or bands.
    expect(row.detail, JSON.stringify(row)).toMatch(/^(ok|insufficient_data|invalid_input|\d+)$/);
  }
});

test('Settings: invalid URL rejected, test connection works, saved URL survives a reload', async ({ page }) => {
  await openApp(page);
  await tap(page, 'Open connection settings');
  const url = page.getByLabel('Gateway URL');
  await url.click();
  await page.keyboard.press('Control+A');
  await page.keyboard.type('not a url');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await see(page, 'Enter a full http:// or https:// address');

  await url.click();
  await page.keyboard.press('Control+A');
  await page.keyboard.type('http://127.0.0.1:1');
  await button(page, 'Test connection').click();
  await see(page, 'Could not connect.', { timeout: 20_000 });

  // Typed with a trailing slash, as people often do.
  const other = `${gatewayUrl}/`;
  await url.click();
  await page.keyboard.press('Control+A');
  await page.keyboard.type(other);
  await button(page, 'Test connection').click();
  await see(page, 'Connection successful.', { timeout: 20_000 });
  await page.getByRole('button', { name: 'Save', exact: true }).click();

  await page.reload();
  const { enableSemantics } = await import('../support/app.mjs');
  await enableSemantics(page);
  // Still connected after the reload, through the saved address (kept on the device).
  // Flutter's web input reports no value to scripts, so the stored setting is read.
  await see(page, 'Connected');
  const stored = () => page.evaluate(() => localStorage.getItem('flutter.c3.gateway_url'));
  expect(JSON.parse(await stored())).toBe(other);

  // Reset to defaults forgets it.
  await tap(page, 'Open connection settings');
  await button(page, 'Reset to defaults').click();
  await expect.poll(stored).toBeNull();
});

test.afterEach(async ({}, info) => {
  if (info.title.startsWith('Past checks: database stopped')) await restartC3();
});
