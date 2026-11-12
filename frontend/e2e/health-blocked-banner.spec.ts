import { test, expect } from '@playwright/test';

test.describe('SyntheticBanner Fail-Safe on Health Outage (F-10b)', () => {
  test('shows synthetic banner and Backend unavailable message when GET /api/health is aborted', async ({
    page,
  }) => {
    await page.route('**/api/health', (route) => route.abort());

    await page.goto('/dashboard');

    await expect(
      page.getByText(/DEMO DATA\s*[—-]\s*SYNTHETIC,\s*NOT REAL NISAR OBSERVATIONS/i)
    ).toBeVisible();
    await expect(page.getByText('Backend unavailable')).toBeVisible({ timeout: 15_000 });
  });
});

