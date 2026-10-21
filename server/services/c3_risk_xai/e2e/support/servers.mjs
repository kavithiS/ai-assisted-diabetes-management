// Throwaway servers for the browser checks. Never the demo ports (8000, 8003).
//   C3 on 8013, gateway on 8010 (pointing at 8013), the Flutter web build on 5192.
// Process IDs are kept in .state.json so the setup, the tests and the teardown (separate
// Node processes) can all stop and restart them.
import { spawn, execFileSync } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync, openSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
export const e2eDir = resolve(here, '..');
export const repoRoot = resolve(e2eDir, '../../../..');
const python = join(repoRoot, '.venv', 'Scripts', 'python.exe');
const stateFile = join(e2eDir, '.state.json');
const logDir = join(e2eDir, 'test-results', 'server-logs');

export const ports = { c3: 8013, gateway: 8010, web: 5192 };
export const gatewayUrl = `http://127.0.0.1:${ports.gateway}`;
export const appUrl = `http://127.0.0.1:${ports.web}`;
export const webBuild = join(repoRoot, 'client', 'mobile_app', 'build', 'web_e2e');

const readState = () => (existsSync(stateFile) ? JSON.parse(readFileSync(stateFile, 'utf8')) : {});
const writeState = (s) => writeFileSync(stateFile, JSON.stringify(s, null, 2));

function start(name, args, env = {}) {
  mkdirSync(logDir, { recursive: true });
  const log = openSync(join(logDir, `${name}.log`), 'a');
  // Run from the repo root so the services read the same .env as the demo.
  const child = spawn(python, args, {
    cwd: repoRoot,
    env: { ...process.env, ...env },
    stdio: ['ignore', log, log],
    detached: true,
    windowsHide: true,
  });
  child.unref();
  writeState({ ...readState(), [name]: child.pid });
}

export function stop(name) {
  const state = readState();
  if (!state[name]) return;
  try {
    execFileSync('taskkill', ['/PID', String(state[name]), '/T', '/F'], { stdio: 'ignore' });
  } catch {
    // Already gone.
  }
  delete state[name];
  writeState(state);
}

async function waitFor(url, ok = (r) => r.ok, timeoutMs = 120_000) {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(10_000) }); // status takes ~3 s with the database down
      if (await ok(r)) return; // `ok` may be async: wait for its answer
    } catch {
      // Not up yet.
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function waitForPortFree(port, timeoutMs = 20_000) {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    try {
      await fetch(`http://127.0.0.1:${port}/`, { signal: AbortSignal.timeout(1000) });
    } catch {
      return;
    }
    await new Promise((r) => setTimeout(r, 300));
  }
}

/** Starts C3. `databaseDown` points it at a closed port: a real outage for this copy only. */
export async function startC3({ databaseDown = false } = {}) {
  const env = { C3_RESEARCH_MODE: 'false' };
  // Port 5499 has no database: the copy on 8013 cannot save or read history.
  if (databaseDown) env.DATABASE_URL = 'postgresql://e2e:none@127.0.0.1:5499/none';
  start('c3', ['-m', 'uvicorn', 'c3_risk_xai.main:app', '--host', '127.0.0.1', '--port', String(ports.c3)], env);
  await waitFor(`${gatewayUrl}/api/v1/risk/status`, async (r) => r.ok && (await r.json()).model_loaded);
}

export async function stopC3() {
  stop('c3');
  await waitForPortFree(ports.c3);
}

export async function restartC3(options) {
  await stopC3();
  await startC3(options);
}

export async function startAll() {
  if (!existsSync(join(webBuild, 'index.html'))) {
    throw new Error(`No web build at ${webBuild}. See e2e/README.md.`);
  }
  for (const port of Object.values(ports)) {
    let busy = false;
    try {
      await fetch(`http://127.0.0.1:${port}/`, { signal: AbortSignal.timeout(1000) });
      busy = true;
    } catch {
      // Free.
    }
    if (busy) throw new Error(`Port ${port} is already in use. Stop it first.`);
  }
  start('web', ['-m', 'http.server', String(ports.web), '--bind', '127.0.0.1', '--directory', webBuild]);
  start(
    'gateway',
    ['-m', 'uvicorn', 'diacare_gateway.main:app', '--host', '127.0.0.1', '--port', String(ports.gateway)],
    {
      C1_URL: 'http://127.0.0.1:8001',
      C2_URL: 'http://127.0.0.1:8002',
      C3_URL: `http://127.0.0.1:${ports.c3}`,
      C4_URL: 'http://127.0.0.1:8004',
    },
  );
  await waitFor(`${appUrl}/index.html`);
  await startC3();
}

export function stopAll() {
  for (const name of ['c3', 'gateway', 'web']) stop(name);
}
