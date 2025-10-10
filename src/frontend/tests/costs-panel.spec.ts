import { test, expect } from '@playwright/test';

// Assumes dev server on 3000 with proxy to backend 8000
test.describe('Entity Costs Panel', () => {
  test('validates required fields and creates a cost item', async ({ page }) => {
    // Navigate to data products and open the first product row
    await page.goto('http://localhost:3000/data-products');
    await page.getByRole('row', { name: /Select row .* v1/i }).first().click();

    // Ensure Costs section is visible
    await expect(page.getByRole('heading', { name: 'Cost Management' })).toBeVisible();

    // Open dialog
    await page.getByRole('button', { name: 'Add expense' }).click();
    await expect(page.getByRole('dialog', { name: 'Add expense' })).toBeVisible();

    // Try to save with missing fields - should show validation toast and inline error
    await page.getByRole('button', { name: 'Save' }).click();
    await expect(page.getByText('Missing required fields')).toBeVisible();
    await expect(page.getByText('Required')).toBeVisible(); // amount required inline

    // Fill minimal valid data
    await page.getByLabel('Amount (cents) *').fill('1234');
    await page.getByLabel('Start month (YYYY-MM) *').fill('2025-10');

    // Save
    await page.getByRole('button', { name: 'Save' }).click();
    await expect(page.getByText(/Cost added|Cost updated/)).toBeVisible();

    // Verify row appears and total updated (non-zero)
    await expect(page.getByText(/US\$|€|£/)).toBeVisible();
  });
});


