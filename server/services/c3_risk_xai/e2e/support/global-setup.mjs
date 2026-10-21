import { rmSync } from 'node:fs';
import { devicesFile } from './app.mjs';
import { startAll, stopAll } from './servers.mjs';

export default async function globalSetup() {
  rmSync(devicesFile, { force: true });
  try {
    await startAll();
  } catch (error) {
    stopAll();
    throw error;
  }
}
