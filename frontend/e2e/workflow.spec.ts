import { test, expect } from '@playwright/test';
import path from 'path';

const WIDTHS = [
  { name: 'desktop', width: 1280, height: 800 },
  { name: 'tablet', width: 820, height: 1024 },
  { name: 'mobile', width: 390, height: 844 },
];

test.describe('TerraWatch AI End-to-End Synthetic Workflow', () => {
  for (const vp of WIDTHS) {
    test(`completes full synthetic workflow at ${vp.name} (${vp.width}x${vp.height})`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });

      // 1. Dashboard: verify synthetic banner, health OK, and navigate to Explore
      await page.goto('/dashboard');
      await expect(page.getByText(/DEMO DATA — SYNTHETIC, NOT REAL NISAR OBSERVATIONS/i)).toBeVisible();
      await expect(page.getByText('OK', { exact: true })).toBeVisible();
      await page.getByRole('link', { name: /start analysis/i }).click();
      await expect(page).toHaveURL(/\/explore/);

      // 2. Explore: click Use demo area, verify metrics, proceed to Observations
      await page.getByRole('button', { name: /use demo area/i }).first().click();
      const nextObsBtn = page.getByRole('button', { name: /next: select observations/i });
      await expect(nextObsBtn).toBeEnabled();
      await nextObsBtn.click();
      await expect(page).toHaveURL(/\/observations/);

      // 3. Observations: wait for catalog, select syn_before & syn_after, proceed to Analysis
      await expect(page.getByText('syn_before')).toBeVisible();
      await expect(page.getByText('syn_after')).toBeVisible();

      await page.getByText('syn_before').click();
      await page.getByText('syn_after').click();

      const proceedBtn = page.getByRole('button', { name: /proceed to analysis/i });
      await expect(proceedBtn).toBeEnabled();
      await proceedBtn.click();
      await expect(page).toHaveURL(/\/analysis\?before=syn_before&after=syn_after/);

      // 4. Analysis: validate compatibility, run job, wait for COMPLETED
      const runBtn = page.getByRole('button', { name: /run analysis/i });
      await expect(runBtn).toBeEnabled();
      await runBtn.click();

      // Ensure no percentage progress bars appear while running/completing
      await expect(page.getByText('COMPLETED', { exact: true })).toBeVisible({ timeout: 25_000 });
      const bodyText = await page.locator('body').innerText();
      expect(bodyText).not.toMatch(/\d+%/);

      await page.getByRole('button', { name: /view results map/i }).first().click();
      await expect(page).toHaveURL(/\/results\?job=/);

      // 5. Results: verify stats match expected_stats.json, limitations, synthetic badge, and layers
      await expect(page.getByTestId('stat-valid-pixels')).toHaveText('4,064');
      await expect(page.getByTestId('stat-invalid-pixels')).toHaveText('32');
      await expect(page.getByTestId('stat-mean')).toHaveText('-0.6890 dB');
      await expect(page.getByTestId('deterministic-summary')).toContainText(
        'Mean difference -0.69 dB over 4,064 valid pixels'
      );
      await expect(page.getByText('DEMO DATA — SYNTHETIC', { exact: true })).toBeVisible();
      await expect(page.getByText(/not a classified event map/i)).toBeVisible();

      // Test layer toggles
      await page.getByRole('tab', { name: 'Before' }).click();
      await page.getByRole('tab', { name: 'After' }).click();
      await page.getByRole('tab', { name: 'Difference (dB)' }).click();

      // Save screenshot on desktop viewport for M4/M5 evidence
      if (vp.name === 'desktop') {
        await page.waitForTimeout(1500);
        const screenshotPath = path.resolve(__dirname, '../../docs/evidence/m4_workflow_result.png');
        await page.screenshot({ path: screenshotPath, fullPage: true });
      }
    });
  }
});
