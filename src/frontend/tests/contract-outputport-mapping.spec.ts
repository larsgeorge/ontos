import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Contract-to-OutputPort Mapping Feature
 * 
 * Tests the complete bidirectional linking between Data Contracts and 
 * Data Product Output Ports, including:
 * - Creating contracts inline from product side
 * - Linking existing contracts to output ports
 * - Linking contracts to existing products from contract side
 * - Unlinking contracts from output ports
 * - Navigation between linked entities
 */

test.describe('Contract-OutputPort Mapping', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to home page and wait for it to load
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should link existing contract to new output port on existing product from contract side', async ({ page }) => {
    // Navigate to contracts list
    await page.click('text=Data Contracts');
    await page.waitForURL('**/data-contracts');
    
    // Click on first active/approved contract
    const contractCard = page.locator('.border').filter({ hasText: /active|approved|certified/i }).first();
    const contractName = await contractCard.locator('.font-medium').first().textContent();
    await contractCard.click();
    
    // Wait for contract details to load
    await page.waitForSelector('text=Linked Data Products');
    
    // Click "Link to Existing Product" button
    await page.click('button:has-text("Link to Existing Product")');
    
    // Wait for dialog to open
    await page.waitForSelector('text=Link Contract to Existing Product');
    
    // Select a product
    await page.click('[id="product"]');
    await page.waitForSelector('role=option');
    await page.click('role=option >> nth=0');
    
    // Wait for product details to load and show port options
    await page.waitForSelector('text=Output Port Assignment');
    
    // Select "Create New Port" option
    await page.click('input[value="new"]');
    
    // Fill in new port details
    await page.fill('[id="portName"]', 'test-output-port');
    await page.fill('[id="portVersion"]', '1.0.0');
    
    // Submit
    await page.click('button:has-text("Link to Product")');
    
    // Wait for success toast
    await page.waitForSelector('text=Contract Linked', { timeout: 10000 });
    
    // Verify the product appears in linked products list
    await page.waitForSelector(`text=${contractName}`, { timeout: 5000 });
    await expect(page.locator('text=Output Port')).toBeVisible();
  });

  test('should link existing contract to existing output port from contract side', async ({ page }) => {
    // First, create a product with an output port without a contract
    await page.click('text=Data Products');
    await page.waitForURL('**/data-products');
    
    // Get existing product or create one
    const productCard = page.locator('.border').first();
    await productCard.click();
    
    // Ensure there's an output port without a contract
    await page.waitForSelector('text=Output Ports');
    const outputPortsCard = page.locator('text=Output Ports').locator('..');
    const linkButtons = outputPortsCard.locator('button[title="Link contract"]');
    
    if (await linkButtons.count() === 0) {
      // Create new output port without contract
      await page.click('button:has-text("Add Output Port")');
      await page.fill('[id="name"]', 'unlinked-port');
      await page.fill('[id="version"]', '1.0.0');
      // Select "No Contract" option (should be default)
      await page.click('button:has-text("Add Port")');
      await page.waitForSelector('text=Output port added', { timeout: 5000 });
    }
    
    // Go back to contracts
    await page.click('text=Data Contracts');
    await page.waitForURL('**/data-contracts');
    
    // Click on an active contract
    const contractCard = page.locator('.border').filter({ hasText: /active|approved|certified/i }).first();
    await contractCard.click();
    
    // Click "Link to Existing Product"
    await page.click('button:has-text("Link to Existing Product")');
    
    // Select the product we just looked at
    await page.click('[id="product"]');
    await page.waitForSelector('role=option');
    await page.click('role=option >> nth=0');
    
    // Select "Assign to Existing Port"
    await page.click('input[value="existing"]');
    
    // Select an available port
    await page.click('[id="port"]');
    await page.waitForSelector('role=option');
    await page.click('role=option >> nth=0');
    
    // Submit
    await page.click('button:has-text("Link to Product")');
    
    // Wait for success
    await page.waitForSelector('text=Contract Linked', { timeout: 10000 });
  });

  test('should link existing contract to output port from product side', async ({ page }) => {
    // Navigate to products
    await page.click('text=Data Products');
    await page.waitForURL('**/data-products');
    
    // Click on first product
    const productCard = page.locator('.border').first();
    await productCard.click();
    
    // Wait for output ports section
    await page.waitForSelector('text=Output Ports');
    
    // Find an output port without a contract or create one
    const linkButton = page.locator('button[title="Link contract"]').first();
    
    if (await linkButton.isVisible()) {
      await linkButton.click();
    } else {
      // Create new port first
      await page.click('button:has-text("Add Output Port")');
      await page.fill('[id="name"]', 'new-test-port');
      await page.fill('[id="version"]', '1.0.0');
      await page.click('button:has-text("Add Port")');
      await page.waitForSelector('text=Output port added', { timeout: 5000 });
      
      // Now click link button on the new port
      await page.locator('button[title="Link contract"]').last().click();
    }
    
    // Wait for link contract dialog
    await page.waitForSelector('text=Link Contract to Output Port');
    
    // Select a contract
    await page.click('[id="contract"]');
    await page.waitForSelector('role=option');
    await page.click('role=option >> nth=0');
    
    // Submit
    await page.click('button:has-text("Link Contract")');
    
    // Wait for success
    await page.waitForSelector('text=Contract Linked', { timeout: 10000 });
    
    // Verify contract badge appears
    await expect(page.locator('text=Contract:')).toBeVisible();
  });

  test('should create contract inline from output port form', async ({ page }) => {
    // Navigate to products
    await page.click('text=Data Products');
    await page.waitForURL('**/data-products');
    
    // Click on first product
    await page.locator('.border').first().click();
    
    // Click "Add Output Port"
    await page.click('button:has-text("Add Output Port")');
    
    // Fill in port details
    await page.fill('[id="name"]', 'port-with-new-contract');
    await page.fill('[id="version"]', '1.0.0');
    
    // Select "Create New Contract"
    await page.click('input[value="create"]');
    
    // Click "Create New Contract" button
    await page.click('button:has-text("Create New Contract")');
    
    // Wait for inline contract creation dialog
    await page.waitForSelector('text=Create New Contract');
    
    // Fill in contract details
    await page.fill('[id="name"]', `Test Contract ${Date.now()}`);
    await page.fill('[id="version"]', '1.0.0');
    
    // Submit contract creation
    await page.click('button:has-text("Create Contract")');
    
    // Wait for contract to be created
    await page.waitForSelector('text=Contract Created', { timeout: 10000 });
    
    // Contract ID should now appear
    await expect(page.locator('text=Contract created:')).toBeVisible();
    
    // Submit the output port
    await page.click('button:has-text("Add Port")');
    
    // Wait for success
    await page.waitForSelector('text=Output port added', { timeout: 5000 });
  });

  test('should unlink contract from output port', async ({ page }) => {
    // Navigate to products
    await page.click('text=Data Products');
    await page.waitForURL('**/data-products');
    
    // Click on first product
    await page.locator('.border').first().click();
    
    // Wait for output ports
    await page.waitForSelector('text=Output Ports');
    
    // Find a port with a contract
    const unlinkButton = page.locator('button[title="Unlink contract"]').first();
    
    if (await unlinkButton.count() === 0) {
      // First link a contract if none exist
      const linkButton = page.locator('button[title="Link contract"]').first();
      if (await linkButton.isVisible()) {
        await linkButton.click();
        await page.waitForSelector('text=Link Contract to Output Port');
        await page.click('[id="contract"]');
        await page.click('role=option >> nth=0');
        await page.click('button:has-text("Link Contract")');
        await page.waitForSelector('text=Contract Linked', { timeout: 10000 });
      }
    }
    
    // Now unlink
    await page.locator('button[title="Unlink contract"]').first().click();
    
    // Confirm dialog
    page.on('dialog', dialog => dialog.accept());
    
    // Wait for success
    await page.waitForSelector('text=Contract Unlinked', { timeout: 10000 });
    
    // Verify link button reappears
    await expect(page.locator('button[title="Link contract"]')).toBeVisible();
  });

  test('should navigate from contract to linked product', async ({ page }) => {
    // Navigate to contracts
    await page.click('text=Data Contracts');
    await page.waitForURL('**/data-contracts');
    
    // Click on a contract
    await page.locator('.border').first().click();
    
    // Wait for linked products section
    await page.waitForSelector('text=Linked Data Products');
    
    // Check if there are linked products
    const linkedProductCards = page.locator('text=Linked Data Products').locator('..').locator('.border.rounded-lg');
    
    if (await linkedProductCards.count() > 0) {
      // Click on first linked product
      await linkedProductCards.first().click();
      
      // Should navigate to product details
      await page.waitForURL('**/data-products/**');
      await expect(page.locator('text=Output Ports')).toBeVisible();
    }
  });

  test('should navigate from product output port to contract', async ({ page }) => {
    // Navigate to products
    await page.click('text=Data Products');
    await page.waitForURL('**/data-products');
    
    // Click on first product
    await page.locator('.border').first().click();
    
    // Wait for output ports
    await page.waitForSelector('text=Output Ports');
    
    // Find and click a contract badge
    const contractBadge = page.locator('text=Contract:').locator('..').first();
    
    if (await contractBadge.isVisible()) {
      await contractBadge.click();
      
      // Should navigate to contract details
      await page.waitForURL('**/data-contracts/**');
      await expect(page.locator('text=Schemas')).toBeVisible();
    }
  });

  test('should respect contract status filtering (active/approved/certified only)', async ({ page }) => {
    // Navigate to products
    await page.click('text=Data Products');
    await page.waitForURL('**/data-products');
    
    // Click on first product
    await page.locator('.border').first().click();
    
    // Try to link a contract
    const linkButton = page.locator('button[title="Link contract"]').first();
    
    if (await linkButton.isVisible()) {
      await linkButton.click();
      
      // Check that only active/approved/certified contracts appear
      await page.waitForSelector('text=Only showing active/approved/certified contracts');
      
      // Click contract selector
      await page.click('[id="contract"]');
      
      // Get all options
      const options = page.locator('role=option');
      const count = await options.count();
      
      // Verify each option has appropriate status
      for (let i = 0; i < count; i++) {
        const optionText = await options.nth(i).textContent();
        expect(optionText).toMatch(/(active|approved|certified)/i);
      }
      
      // Close dialog
      await page.click('button:has-text("Cancel")');
    }
  });

  test('should show output port information in contract linked products section', async ({ page }) => {
    // Navigate to contracts
    await page.click('text=Data Contracts');
    await page.waitForURL('**/data-contracts');
    
    // Click on a contract
    await page.locator('.border').first().click();
    
    // Wait for linked products section
    await page.waitForSelector('text=Linked Data Products');
    
    // Check if there are linked products with port info
    const portInfo = page.locator('text=Output Port');
    
    if (await portInfo.isVisible()) {
      // Verify format shows port name and version
      const portText = await portInfo.textContent();
      expect(portText).toMatch(/Output Port.*\(v\d+\.\d+\.\d+\)/);
    }
  });

  test('should prevent linking contract to port that already has one', async ({ page }) => {
    // Navigate to products
    await page.click('text=Data Products');
    await page.waitForURL('**/data-products');
    
    // Click on first product
    await page.locator('.border').first().click();
    
    // Count ports with contracts vs without
    const linkButtons = page.locator('button[title="Link contract"]');
    const unlinkButtons = page.locator('button[title="Unlink contract"]');
    
    const linkCount = await linkButtons.count();
    const unlinkCount = await unlinkButtons.count();
    
    // Each port should have either link or unlink button, not both
    expect(linkCount + unlinkCount).toBeGreaterThan(0);
    
    // Verify that ports with contracts show unlink button
    if (unlinkCount > 0) {
      // Port with contract should not have link button
      const portWithContract = page.locator('text=Contract:').locator('../..');
      const linkInSamePort = portWithContract.locator('button[title="Link contract"]');
      expect(await linkInSamePort.count()).toBe(0);
    }
  });
});

