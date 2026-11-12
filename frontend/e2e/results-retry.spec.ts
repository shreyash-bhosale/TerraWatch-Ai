import { test, expect } from '@playwright/test';
import { execSync, spawn } from 'child_process';
import path from 'path';

const REPO_ROOT = path.resolve(__dirname, '../..');
const BACKEND_URL = 'http://127.0.0.1:8000';

const DEMO_AOI = {
  type: 'Polygon',
  coordinates: [
    [
      [73.8, 18.496],
      [73.864, 18.496],
      [73.864, 18.56],
      [73.8, 18.56],
      [73.8, 18.496],
    ],
  ],
};

function stopBackendOnPort8000(): void {
  execSync('pids=$(lsof -tiTCP:8000 -sTCP:LISTEN || true); if [ -n "$pids" ]; then kill $pids; fi', {
    stdio: 'ignore',
  });
}

async function waitForBackendDown(timeoutMs = 10_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      await fetch(`${BACKEND_URL}/api/health`);
    } catch {
      return;
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error('Backend on port 8000 did not stop in time');
}

function startBackend(): void {
  const uvicorn = path.join(REPO_ROOT, '.venv/bin/uvicorn');
  const child = spawn(uvicorn, ['app.main:app', '--host', '127.0.0.1', '--port', '8000'], {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      PYTHONPATH: path.join(REPO_ROOT, 'backend'),
    },
    detached: true,
    stdio: 'ignore',
  });
  child.unref();
}

async function waitForBackendUp(timeoutMs = 15_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BACKEND_URL}/api/health`);
      if (res.ok) return;
    } catch {
      // still starting
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error('Restarted backend on port 8000 did not become healthy in time');
}

test.describe('Results Page Backend Outage & Retry (F-05)', () => {
  test('shows error Alert with Retry when backend is stopped, then loads results after backend restarts and Retry is clicked', async ({
    page,
  }) => {
    // 1. Create and complete a real synthetic job while backend is running
    const createRes = await fetch(`${BACKEND_URL}/api/analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        before_id: 'syn_before',
        after_id: 'syn_after',
        aoi: DEMO_AOI,
      }),
    });
    expect(createRes.status).toBe(202);
    const { job_id: jobId } = (await createRes.json()) as { job_id: string };

    // Poll until completed
    let completed = false;
    for (let i = 0; i < 40; i += 1) {
      const statusRes = await fetch(`${BACKEND_URL}/api/analysis/${encodeURIComponent(jobId)}`);
      const statusJson = (await statusRes.json()) as { status: string };
      if (statusJson.status === 'completed') {
        completed = true;
        break;
      }
      await new Promise((r) => setTimeout(r, 250));
    }
    expect(completed).toBe(true);

    try {
      // 2. Stop the real backend on port 8000
      stopBackendOnPort8000();
      await waitForBackendDown();

      // 3. Visit /results?job=<id> and observe error Alert + Retry button
      await page.goto(`/results?job=${encodeURIComponent(jobId)}`);
      await expect(page.getByText(/results not available/i)).toBeVisible();
      const retryBtn = page.getByRole('button', { name: /retry/i });
      await expect(retryBtn).toBeVisible();

      // 4. Restart the real backend and wait for /api/health
      startBackend();
      await waitForBackendUp();

      // 5. Click Retry and confirm the real results load
      await retryBtn.click();
      await expect(page.getByTestId('stat-valid-pixels')).toHaveText('4,064', { timeout: 15_000 });
      await expect(page.getByTestId('stat-mean')).toHaveText('-0.6890 dB');
    } finally {
      // Ensure backend is healthy again if the test failed while backend was stopped
      try {
        const res = await fetch(`${BACKEND_URL}/api/health`);
        if (!res.ok) {
          startBackend();
          await waitForBackendUp();
        }
      } catch {
        startBackend();
        await waitForBackendUp();
      }
    }
  });
});
