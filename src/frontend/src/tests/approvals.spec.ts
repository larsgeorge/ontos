import { test, expect } from '@playwright/test';

test.describe('Approvals queue and lifecycle actions', () => {
  test('Required Actions shows approvals queue', async ({ page }) => {
    await page.goto('/');
    // Wait for home sections
    await expect(page.getByRole('heading', { name: 'Required Actions' })).toBeVisible();
    // Approvals card exists
    await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible();
  });

  test('Contract submit/approve buttons appear by status', async ({ page }) => {
    // Navigate to contracts list and open first contract
    await page.goto('/data-contracts');
    // Click first row if exists
    const rows = page.locator('table tbody tr');
    const hasRows = await rows.count();
    if (hasRows > 0) {
      await rows.nth(0).click();
      // Either submit or approve/reject should be visible depending on backend state
      const submitBtn = page.getByRole('button', { name: /Submit for Review/i });
      const approveBtn = page.getByRole('button', { name: /^Approve$/i });
      const rejectBtn = page.getByRole('button', { name: /^Reject$/i });
      await expect(submitBtn.or(approveBtn)).toBeVisible();
      await expect(submitBtn.or(rejectBtn)).toBeVisible();
    }
  });

  test('Product certification actions appear by status', async ({ page }) => {
    await page.goto('/data-products');
    const rows = page.locator('table tbody tr');
    const hasRows = await rows.count();
    if (hasRows > 0) {
      await rows.nth(0).click();
      const submitCertBtn = page.getByRole('button', { name: /Submit for Certification/i });
      const certifyBtn = page.getByRole('button', { name: /^Certify$/i });
      const rejectBtn = page.getByRole('button', { name: /^Reject$/i });
      await expect(submitCertBtn.or(certifyBtn)).toBeVisible();
      await expect(submitCertBtn.or(rejectBtn)).toBeVisible();
    }
  });
});


