// Browser checks of the C3 Flutter web build. Uses the installed Chrome (channel
// 'chrome'); no browser is downloaded. One worker: some tests stop and restart the
// throwaway C3 server, so tests must not overlap.
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  expect: { timeout: 20_000 },
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: 'test-results/results.json' }]],
  globalSetup: './support/global-setup.mjs',
  globalTeardown: './support/global-teardown.mjs',
  use: {
    channel: 'chrome',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    // Flutter's web build calls the gateway on another port.
    launchOptions: { args: ['--disable-web-security'] },
  },
  projects: [
    { name: 'phone', use: { viewport: { width: 412, height: 915 }, hasTouch: false } },
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
  ],
});
