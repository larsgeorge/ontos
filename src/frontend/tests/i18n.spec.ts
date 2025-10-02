import { test, expect } from '@playwright/test';

test.describe('Internationalization (i18n)', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    // Wait for the app to load
    await page.waitForLoadState('networkidle');
  });

  test('should display language selector in header', async ({ page }) => {
    // Look for the language selector button (Globe icon)
    const languageSelector = page.getByRole('button', { name: /language/i });
    await expect(languageSelector).toBeVisible();
  });

  test('should switch between English and German', async ({ page }) => {
    // Click the language selector
    const languageSelector = page.getByRole('button', { name: /language/i });
    await languageSelector.click();

    // Verify English option is visible
    const englishOption = page.getByText('English');
    await expect(englishOption).toBeVisible();

    // Verify German option is visible
    const germanOption = page.getByText('Deutsch');
    await expect(germanOption).toBeVisible();

    // Click on German
    await germanOption.click();

    // Navigate to Settings page
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Verify German translation is applied
    const settingsTitle = page.getByRole('heading', { name: /einstellungen/i });
    await expect(settingsTitle).toBeVisible();

    // Check if Jobs tab is translated
    const jobsTab = page.getByRole('tab', { name: /jobs & workflows/i });
    await expect(jobsTab).toBeVisible();

    // Switch back to English
    await languageSelector.click();
    await page.getByText('English').click();

    // Verify English translation is restored
    const settingsTitleEN = page.getByRole('heading', { name: /^settings$/i });
    await expect(settingsTitleEN).toBeVisible();
  });

  test('should persist language selection across page reloads', async ({ page }) => {
    // Change language to German
    const languageSelector = page.getByRole('button', { name: /language/i });
    await languageSelector.click();
    await page.getByText('Deutsch').click();

    // Reload the page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Navigate to Settings
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Verify German is still active
    const settingsTitle = page.getByRole('heading', { name: /einstellungen/i });
    await expect(settingsTitle).toBeVisible();
  });

  test('should translate Settings page Jobs tab content', async ({ page }) => {
    // Navigate to Settings
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Click on Jobs & Workflows tab
    const jobsTab = page.getByRole('tab', { name: /jobs & workflows/i });
    await jobsTab.click();

    // Verify English labels are present
    await expect(page.getByText('Job Cluster ID')).toBeVisible();
    await expect(page.getByText('Jobs & Workflows Configuration')).toBeVisible();

    // Switch to German
    const languageSelector = page.getByRole('button', { name: /language/i });
    await languageSelector.click();
    await page.getByText('Deutsch').click();

    // Verify German labels are present
    await expect(page.getByText('Job-Cluster-ID')).toBeVisible();
    await expect(page.getByText('Jobs & Workflows Konfiguration')).toBeVisible();
  });

  test('should translate toast messages', async ({ page }) => {
    // Navigate to Settings
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Click on Jobs tab
    const jobsTab = page.getByRole('tab', { name: /jobs & workflows/i });
    await jobsTab.click();

    // Switch to German
    const languageSelector = page.getByRole('button', { name: /language/i });
    await languageSelector.click();
    await page.getByText('Deutsch').click();

    // Click save button
    const saveButton = page.getByRole('button', { name: /konfiguration speichern/i });
    await saveButton.click();

    // Verify German toast message appears (success or error)
    const toast = page.locator('[role="status"]').or(page.locator('.toast')).first();
    await expect(toast).toBeVisible({ timeout: 5000 });
  });
});
