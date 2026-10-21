// Helpers to drive the Flutter web build through its accessibility (semantics) tree.
import { execFileSync } from 'node:child_process';
import { appendFileSync, mkdirSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { join } from 'node:path';
import { expect } from '@playwright/test';
import { appUrl, e2eDir, gatewayUrl, repoRoot } from './servers.mjs';

export const devicesFile = join(e2eDir, '.devices.txt');

/** Words that must never reach a patient screen or a screen-reader label. */
export const banned =
  /\b(AI|artificial intelligence|machine learning|model|algorithm|SHAP|LIME|prototype|research|researcher|demo|debug|probability|agreement|warm up|provisional|diagnosis)\b/i;
/** A raw probability or percentage, e.g. "0.5657" or "56.6%". */
export const rawNumber = /\b0\.\d{3,}\b|\d+(\.\d+)?\s?%/;

/** A fresh throwaway device ID (hex, as the server requires), recorded for clean-up. */
export function newDeviceId() {
  const id = `e2e0${randomBytes(14).toString('hex')}`;
  mkdirSync(e2eDir, { recursive: true });
  appendFileSync(devicesFile, `${id}\n`);
  return id;
}

/**
 * Opens the app with its own device ID, then switches on the semantics tree the same way
 * a screen reader does (the hidden "Enable accessibility" button). Nothing in the app
 * changes for this; it only exists in the test browser.
 */
export async function openApp(page, { deviceId = newDeviceId(), gateway, path = '/' } = {}) {
  await page.addInitScript(
    ([id, url]) => {
      if (!localStorage.getItem('flutter.c3.device_id')) {
        localStorage.setItem('flutter.c3.device_id', JSON.stringify(id));
      }
      if (url && !localStorage.getItem('flutter.c3.gateway_url')) {
        localStorage.setItem('flutter.c3.gateway_url', JSON.stringify(url));
      }
    },
    [deviceId, gateway ?? null],
  );
  await page.goto(`${appUrl}${path}`);
  await enableSemantics(page);
  return deviceId;
}

export async function enableSemantics(page) {
  const placeholder = page.locator('flt-semantics-placeholder');
  await placeholder.waitFor({ state: 'attached', timeout: 30_000 });
  await placeholder.dispatchEvent('click');
  await expect(page.locator('flt-semantics').first()).toBeAttached({ timeout: 15_000 });
}

export const button = (page, name) => page.getByRole('button', { name, exact: false });

/** Text visible on screen plus every accessibility label, value and hint. */
export async function allScreenText(page) {
  return page.evaluate(() => {
    const parts = [document.title];
    const host = document.querySelector('flt-semantics-host');
    if (host) parts.push(host.textContent);
    for (const el of document.querySelectorAll('flt-semantics-host *, input, textarea')) {
      for (const attr of ['aria-label', 'aria-description', 'aria-valuetext', 'title', 'placeholder']) {
        const v = el.getAttribute(attr);
        if (v) parts.push(v);
      }
      if (el.value) parts.push(el.value);
    }
    return parts.join('\n');
  });
}

export async function expectNoBannedText(page, where) {
  const textNow = await allScreenText(page);
  expect(textNow.length, `${where}: semantics text should not be empty`).toBeGreaterThan(20);
  expect(textNow, `${where}: banned word`).not.toMatch(banned);
  expect(textNow, `${where}: raw probability or percentage`).not.toMatch(rawNumber);
}

/** Saved results on the server for a device (straight from the gateway). */
export async function savedCount(deviceId) {
  const r = await fetch(`${gatewayUrl}/api/v1/risk/history`, { headers: { 'X-Device-Id': deviceId } });
  expect(r.ok).toBeTruthy();
  return (await r.json()).items.length;
}

/** Audit rows of a test device, read with the service's own settings. */
export function auditRows(deviceId) {
  const out = execFileSync(
    join(repoRoot, '.venv', 'Scripts', 'python.exe'),
    [join(e2eDir, 'support', 'audit.py'), 'show', deviceId],
    { cwd: repoRoot, encoding: 'utf8' },
  );
  return JSON.parse(out);
}

/** Collects console errors and failed requests; call .check() at the end of a test. */
export function watchConsole(page, { allowFailedRequests = false } = {}) {
  const errors = [];
  const failed = [];
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('requestfailed', (r) => failed.push(`${r.method()} ${r.url()} ${r.failure()?.errorText}`));
  page.on('response', (r) => {
    if (r.status() >= 400) failed.push(`${r.status()} ${r.request().method()} ${r.url()}`);
  });
  return {
    errors,
    failed,
    check() {
      expect(errors, 'console errors').toEqual([]);
      if (!allowFailedRequests) expect(failed, 'failed network calls').toEqual([]);
    },
  };
}

/** Visible text (in the semantics tree), first match. */
export const text = (page, value) => page.getByText(value, { exact: false }).first();

/** Scrolls the Flutter view with the mouse wheel until `locator` is in the tree. */
export async function scrollTo(page, locator, { maxSteps = 15 } = {}) {
  const size = page.viewportSize();
  await page.mouse.move(size.width / 2, size.height / 2);
  for (let i = 0; i < maxSteps; i += 1) {
    if ((await locator.count()) > 0 && (await locator.first().isVisible())) {
      await locator.first().scrollIntoViewIfNeeded();
      return locator.first();
    }
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(250);
  }
  throw new Error(`Not found after scrolling: ${locator}`);
}

/** Types into a Flutter text field found by its label (keyboard entry, like a user). */
export async function typeInto(page, label, value) {
  const field = await scrollTo(page, page.getByLabel(label, { exact: true }));
  await field.click();
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Backspace');
  if (value !== '') await page.keyboard.type(String(value));
}

/**
 * Opens Settings the hidden way: a long-press on the connection chip at the top of home
 * (app users see neither Settings nor the example answers on home).
 */
export async function openSettings(page) {
  const chip = button(page, 'Tap to check again');
  if (!(await chip.isVisible())) {
    // Back to the top of home; then let the scroll settle, or Flutter can treat the
    // long-press as part of the scroll.
    const size = page.viewportSize();
    await page.mouse.move(size.width / 2, size.height / 2);
    await page.mouse.wheel(0, -5000);
    await page.waitForTimeout(800);
  }
  await expect(chip).toBeVisible();
  const box = await chip.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.waitForTimeout(1000);
  await page.mouse.up();
  await see(page, 'Gateway URL');
}

/** Opens Settings and returns the example-answers button `label`, ready to click. */
export async function example(page, label) {
  await openSettings(page);
  return scrollTo(page, button(page, label));
}

/** Runs an example from Settings and waits for the result screen. */
export async function runPreset(page, label) {
  await (await example(page, label)).click();
  // A button that only the result screen has.
  await expect(button(page, 'Update health information')).toBeVisible({ timeout: 30_000 });
}

/** Waits until `value` (string or RegExp) is on screen, in text or screen-reader labels. */
export async function see(page, value, { timeout = 20_000 } = {}) {
  await expect
    .poll(async () => {
      // Case-insensitive: section labels are shown in capitals.
      const all = (await allScreenText(page)).replace(/\s+/g, ' ');
      return typeof value === 'string'
        ? all.toLowerCase().includes(value.toLowerCase())
        : new RegExp(value.source, `${value.flags.replace('i', '')}i`).test(all);
    }, { message: `on screen: ${value}`, timeout })
    .toBe(true);
}

/** Waits (up to 10 s) until `value` is no longer on screen. */
export async function notSee(page, value, { timeout = 10_000 } = {}) {
  await expect
    .poll(async () => {
      const all = (await allScreenText(page)).replace(/\s+/g, ' ');
      return typeof value === 'string'
        ? all.toLowerCase().includes(value.toLowerCase())
        : value.test(all);
    }, { message: `not on screen: ${value}`, timeout })
    .toBe(false);
}

/** Scrolls to a button (home has a long list once a score is shown) and taps it. */
export async function tap(page, name) {
  await (await scrollTo(page, button(page, name))).click();
}

/** Home is showing (its title is always at the top, whatever the list scroll). */
export async function atHome(page) {
  await expect(page.getByRole('heading', { name: 'DiaCare' })).toBeVisible();
}

/** Back, then wait for the 300 ms page animation (Flutter ignores taps while it runs). */
export async function back(page) {
  await button(page, 'Back').click();
  await page.waitForTimeout(600);
}

/** Presses Back until home shows (from a result: result -> Settings -> home). */
export async function goHome(page) {
  for (let i = 0; i < 4; i += 1) {
    if (await page.getByRole('heading', { name: 'DiaCare' }).isVisible()) return;
    await button(page, 'Back').click();
    await page.waitForTimeout(600);
  }
  await atHome(page);
}
