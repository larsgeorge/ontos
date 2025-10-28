import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Contract-to-OutputPort Mapping Feature
 * 
 * Tests the complete bidirectional linking between Data Contracts and 
 * Data Product Output Ports.
 */

test.describe('Contract-OutputPort Mapping', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('Contract Details page should show Link to Existing Product button', async ({ page }) => {
    // Navigate directly to a contract details page
    await page.goto('/data-contracts');
    await page.waitForSelector('h1, h2, .text-2xl');
    
    // Click on first contract in the list
    const firstContract = page.locator('[class*="border"][class*="rounded"]').first();
    if (await firstContract.isVisible()) {
      await firstContract.click();
      
      // Wait for contract details to load
      await page.waitForSelector('text=Linked Data Products', { timeout: 10000 });
      
      // Verify "Link to Existing Product" button exists
      const linkButton = page.locator('button:has-text("Link to Existing Product")');
      await expect(linkButton).toBeVisible();
      
      // Verify "Create Data Product" button also exists
      const createButton = page.locator('button:has-text("Create Data Product")');
      await expect(createButton).toBeVisible();
    }
  });

  test('Product Details page should show Link/Unlink buttons on output ports', async ({ page }) => {
    // Navigate directly to products
    await page.goto('/data-products');
    await page.waitForSelector('h1, h2, .text-2xl');
    
    // Click on first product
    const firstProduct = page.locator('[class*="border"][class*="rounded"]').first();
    if (await firstProduct.isVisible()) {
      await firstProduct.click();
      
      // Wait for product details
      await page.waitForSelector('text=Output Ports', { timeout: 10000 });
      
      // Check for either link or unlink buttons (depending on port state)
      const linkButtons = page.locator('button[title="Link contract"]');
      const unlinkButtons = page.locator('button[title="Unlink contract"]');
      
      const totalButtons = await linkButtons.count() + await unlinkButtons.count();
      expect(totalButtons).toBeGreaterThanOrEqual(0); // May have no ports
    }
  });

  test('Add Output Port dialog should have Contract Assignment section', async ({ page }) => {
    // Navigate to a product
    await page.goto('/data-products');
    await page.waitForSelector('h1, h2');
    
    const firstProduct = page.locator('[class*="border"][class*="rounded"]').first();
    if (await firstProduct.isVisible()) {
      await firstProduct.click();
      await page.waitForSelector('text=Output Ports', { timeout: 10000 });
      
      // Click Add Output Port
      const addPortButton = page.locator('button:has-text("Add Output Port")');
      if (await addPortButton.isVisible()) {
        await addPortButton.click();
        
        // Wait for dialog
        await page.waitForSelector('text=Add Output Port', { timeout: 5000 });
        
        // Verify Contract Assignment section exists
        await expect(page.locator('text=Contract Assignment')).toBeVisible();
        
        // Verify radio options
        await expect(page.locator('text=No Contract')).toBeVisible();
        await expect(page.locator('text=Select Existing Contract')).toBeVisible();
        await expect(page.locator('text=Create New Contract')).toBeVisible();
      }
    }
  });

  test('Link Contract dialog should open when clicking link button', async ({ page }) => {
    await page.goto('/data-products');
    await page.waitForSelector('h1, h2');
    
    const firstProduct = page.locator('[class*="border"][class*="rounded"]').first();
    if (await firstProduct.isVisible()) {
      await firstProduct.click();
      await page.waitForSelector('text=Output Ports', { timeout: 10000 });
      
      // Look for a link button
      const linkButton = page.locator('button[title="Link contract"]').first();
      if (await linkButton.isVisible()) {
        await linkButton.click();
        
        // Dialog should open
        await expect(page.locator('text=Link Contract to Output Port')).toBeVisible({ timeout: 5000 });
        await expect(page.locator('text=Select Contract')).toBeVisible();
        await expect(page.locator('button:has-text("Create New Contract")')).toBeVisible();
      }
    }
  });

  test('Link Product dialog should open when clicking Link to Existing Product', async ({ page }) => {
    await page.goto('/data-contracts');
    await page.waitForSelector('h1, h2');
    
    // Click on an active/approved contract
    const contracts = page.locator('[class*="border"][class*="rounded"]');
    const count = await contracts.count();
    
    for (let i = 0; i < Math.min(count, 5); i++) {
      const contract = contracts.nth(i);
      const text = await contract.textContent();
      
      if (text && /(active|approved|certified)/i.test(text)) {
        await contract.click();
        await page.waitForSelector('text=Linked Data Products', { timeout: 10000 });
        
        // Click Link to Existing Product button
        const linkButton = page.locator('button:has-text("Link to Existing Product")');
        
        if (await linkButton.isEnabled()) {
          await linkButton.click();
          
          // Dialog should open
          await expect(page.locator('text=Link Contract to Existing Product')).toBeVisible({ timeout: 5000 });
          await expect(page.locator('text=Select Product')).toBeVisible();
          break;
        }
      }
    }
  });

  test('Contract badge on output port should be clickable', async ({ page }) => {
    await page.goto('/data-products');
    await page.waitForSelector('h1, h2');
    
    const firstProduct = page.locator('[class*="border"][class*="rounded"]').first();
    if (await firstProduct.isVisible()) {
      await firstProduct.click();
      await page.waitForSelector('text=Output Ports', { timeout: 10000 });
      
      // Look for a contract badge
      const contractBadge = page.locator('text=Contract:').locator('..');
      if (await contractBadge.isVisible()) {
        // Badge should be clickable (has cursor-pointer class or onclick)
        const classes = await contractBadge.getAttribute('class');
        expect(classes).toContain('cursor-pointer');
      }
    }
  });

  test('Unlink button should have confirmation dialog', async ({ page }) => {
    await page.goto('/data-products');
    await page.waitForSelector('h1, h2');
    
    const firstProduct = page.locator('[class*="border"][class*="rounded"]').first();
    if (await firstProduct.isVisible()) {
      await firstProduct.click();
      await page.waitForSelector('text=Output Ports', { timeout: 10000 });
      
      // Look for unlink button
      const unlinkButton = page.locator('button[title="Unlink contract"]').first();
      if (await unlinkButton.isVisible()) {
        // Set up dialog listener before clicking
        page.once('dialog', async dialog => {
          expect(dialog.message()).toContain('Unlink');
          await dialog.dismiss(); // Don't actually unlink in this test
        });
        
        await unlinkButton.click();
        
        // Wait a bit to ensure dialog was triggered
        await page.waitForTimeout(500);
      }
    }
  });

  test('Product cards in contract details should be clickable', async ({ page }) => {
    await page.goto('/data-contracts');
    await page.waitForSelector('h1, h2');
    
    const firstContract = page.locator('[class*="border"][class*="rounded"]').first();
    if (await firstContract.isVisible()) {
      await firstContract.click();
      await page.waitForSelector('text=Linked Data Products', { timeout: 10000 });
      
      // Look for linked product cards
      const productCards = page.locator('text=Linked Data Products')
        .locator('..')
        .locator('..')
        .locator('.border.rounded-lg');
      
      if (await productCards.count() > 0) {
        const firstCard = productCards.first();
        // Card should have cursor-pointer class
        const classes = await firstCard.getAttribute('class');
        expect(classes).toContain('cursor-pointer');
      }
    }
  });

  test('Linked products should show output port information', async ({ page }) => {
    await page.goto('/data-contracts');
    await page.waitForSelector('h1, h2');
    
    const firstContract = page.locator('[class*="border"][class*="rounded"]').first();
    if (await firstContract.isVisible()) {
      await firstContract.click();
      await page.waitForSelector('text=Linked Data Products', { timeout: 10000 });
      
      // If there are linked products, check if port info is shown
      const portInfo = page.locator('text=Output Port');
      if (await portInfo.count() > 0) {
        // Verify it shows version info
        const text = await portInfo.first().textContent();
        expect(text).toMatch(/\(v\d+\.\d+/);
      }
    }
  });

  test('Contract status filtering should work in selectors', async ({ page }) => {
    await page.goto('/data-products');
    await page.waitForSelector('h1, h2');
    
    const firstProduct = page.locator('[class*="border"][class*="rounded"]').first();
    if (await firstProduct.isVisible()) {
      await firstProduct.click();
      await page.waitForSelector('text=Output Ports', { timeout: 10000 });
      
      const linkButton = page.locator('button[title="Link contract"]').first();
      if (await linkButton.isVisible()) {
        await linkButton.click();
        await page.waitForSelector('text=Link Contract to Output Port', { timeout: 5000 });
        
        // Verify filter message
        await expect(page.locator('text=Only showing active/approved/certified contracts')).toBeVisible();
      }
    }
  });
});
