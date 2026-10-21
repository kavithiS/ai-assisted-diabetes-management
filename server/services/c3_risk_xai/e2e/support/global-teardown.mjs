// Removes everything the test devices left behind, then stops the throwaway servers.
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { devicesFile } from './app.mjs';
import { e2eDir, repoRoot, restartC3, stopAll } from './servers.mjs';

export default async function globalTeardown() {
  try {
    const ids = existsSync(devicesFile)
      ? [...new Set(readFileSync(devicesFile, 'utf8').split(/\s+/).filter(Boolean))]
      : [];
    if (ids.length) {
      // A test may have left C3 running without its database: start a normal copy.
      await restartC3();
      const out = execFileSync(
        join(repoRoot, '.venv', 'Scripts', 'python.exe'),
        [join(e2eDir, 'support', 'audit.py'), 'purge', ...ids],
        { cwd: repoRoot, encoding: 'utf8' },
      );
      console.log(`Removed test rows for ${ids.length} throwaway devices: ${out.trim()}`);
    }
  } finally {
    stopAll();
  }
}
