import { test, expect } from '@playwright/test';

test.describe('Roles - Approval Privileges', () => {
  test('Role form shows approval privilege checkboxes and persists', async ({ page }) => {
    await page.goto('/settings');
    // Open Roles tab by default; click Add Role
    const addRole = page.getByRole('button', { name: /Add Role/i });
    await addRole.click();
    // Dialog opens
    await expect(page.getByRole('dialog', { name: /Create Role/i })).toBeVisible();
    // Fill role name
    await page.getByLabel(/Role Name/i).fill('e2e-approver');
    // Toggle a couple of approval privileges
    await page.getByLabel(/Contracts/i).check();
    await page.getByLabel(/Products/i).check();
    // Save
    await page.getByRole('button', { name: /^Create Role$/i }).click();
    // Expect toast success or dialog closed
    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 5000 });
    // Verify role appears in table
    await expect(page.getByRole('row', { name: /e2e-approver/i })).toBeVisible();
  });
});


