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

      if (vp.name === 'mobile') {
        const widths = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        }));
        expect(widths.scrollWidth).toBe(widths.clientWidth);

        // Verify mobile menu is keyboard operable (F-02)
        const toggle = page.getByRole('button', { name: /toggle navigation menu/i });
        await toggle.focus();
        await page.keyboard.press('Enter');
        await expect(page.getByRole('navigation', { name: /mobile navigation/i })).toBeVisible();
        await page.keyboard.press('Escape');
        await expect(page.getByRole('navigation', { name: /mobile navigation/i })).toBeHidden();
      }

      await page.getByRole('link', { name: /start analysis/i }).click();
      await expect(page).toHaveURL(/\/explore/);

      // 2. Explore: click Use demo area, verify MapLibre AOI source matches DEMO_AOI (F-05), proceed to Observations
      await page.getByRole('button', { name: /use demo area/i }).first().click();
      const mapContainer = page.getByTestId('maplibre-container');
      await expect(mapContainer).toHaveAttribute('data-aoi-geometry', /"type":"Polygon"/, { timeout: 10_000 });
      const mapGeometryMatchesDemo = await page.evaluate(() => {
        const el = document.querySelector('[data-testid="maplibre-container"]') as any;
        const raw = el?.getAttribute('data-aoi-geometry');
        const map = el?.__maplibreMap;
        const sourceData = map?.getSource?.('custom-aoi-source')?._data;
        if (!raw || !sourceData) return false;
        return JSON.stringify(JSON.parse(raw)) === JSON.stringify(sourceData);
      });
      expect(mapGeometryMatchesDemo).toBe(true);

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

      const currentUrl = new URL(page.url());
      const createdJobId = currentUrl.searchParams.get('job');
      expect(createdJobId).toBeTruthy();

      // Verify /analysis?job=<id> works without before/after params (F-03) and Dashboard shows Study Area + Recent Jobs (F-06)
      await page.goto(`/analysis?job=${encodeURIComponent(createdJobId!)}`);
      await expect(page.getByText(`Job ${createdJobId}`)).toBeVisible();
      await expect(page.getByText('syn_before')).toBeVisible();
      await expect(page.getByText('syn_after')).toBeVisible();

      await page.goto('/dashboard');
      await expect(page.getByText(/study area summary/i)).toBeVisible();
      await expect(page.getByText('5 vertices')).toBeVisible();
      await expect(page.getByText(createdJobId!)).toBeVisible();
      await expect(page.getByText('COMPLETED').first()).toBeVisible();

      // Return to Results page
      await page.goto(`/results?job=${encodeURIComponent(createdJobId!)}`);

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
